# ReAuthorize 1.4.4: authorization compatibility audit

Audit date: October 22, 2026. Scope: all four supplied archives, including the Crew module and ResolveURL follow-ups.

## Result

Several authorization failures are explained by confirmed writer/reader mismatches. Highest priorities: prevent normal metadata sync from erasing existing credentials; fix Seren's Trakt application identity; fix Umbrella's FilePursuit setting; fix TMDb Helper's Trakt expiry; and make removal clear receiving add-ons consistently.

This is a static code audit with isolated dummy-data checks, not a live-account certification. “Mapping matches” below means the destination credential names and storage format agree with the supplied reader. It does not establish that a provider accepts the credential today, or that playback works. No real accounts were contacted and no supplied source was changed.

## Versions and limits

| Component | Supplied version |
|---|---|
| ReAuthorize | 1.4.4 |
| Seren | 4.3.214 |
| The Crew | 3.2.2 |
| The Crew module (third supplied archive) | 3.2.26 |
| ResolveURL (fourth supplied archive) | 5.1.211 |
| TMDb Helper | 6.18.1 |
| TMDb Movies | 1.1.321 |
| Umbrella | 6.7.729 |
| POV | 6.10.21 |
| Prism | 5.0.56 |
| Red Light | 2.8.9 |

Follow-up: the third archive supplies `script.module.thecrew` 3.2.26, satisfying The Crew UI's minimum 3.2.9 requirement. Its consumers and Trakt implementation have now been reviewed; see the Crew addendum below. The supplied Trakt source is already marked as patched by ReAuthorize, so this is not a pristine upstream-source sample. ResolveURL 5.1.211 is supplied in the fourth archive and is reviewed in the final addendum. Account-manager modules, YouTube, Last.fm/MDBList/Simkl scrobblers, and other ReAuthorize targets were not supplied. Prism also uses `context.prism` for fallback credentials; explicit setting overrides are visible in its supplied code, but the dependency was not supplied.

Source references below use `R/` for `audit_source/script.module.reauthorize/lib/reauthorize/modules/`, `C/` for `audit_source/script.module.reauthorize-core/resources/libs/common/`, and `P/<id>/` for `plugin_audit/<id>/`. Line numbers refer to the extracted files in this audit workspace. Secret values are intentionally omitted.

## Confirmed defects and missing integrations

### F01 — Normal metadata sync deletes unrelated credentials (high)

`R/sync/meta_sync.py` compares every source metadata value against every destination. A blank source differs from a populated destination and is written as an empty string. This is not restricted to explicit wipe mode.

Reproduced with the Umbrella block: setting only a Fanart key erased an existing `tmdb.apikey` and `tmdb.sessionid`. The earlier Coalition dummy-data reproduction also erased OMDb, TMDb, and IMDb values. Similar unguarded logic is present for Seren, TMDb Helper, Prism and other metadata targets.

User impact: adding one service can break another service that was working inside a plugin. Missing fields after a restore can erase usable plugin settings.

Fix: normal push skips absent source credentials; explicit removal clears only the selected service. Treat TMDb account credentials as a bundle, separate from its API key. Return per-field or per-service results.

Evidence: `R/sync/meta_sync.py:29–53`, `127–185`, `494–525`, and `849–863`.

### F02 — Seren Trakt source patch is obsolete (high)

ReAuthorize replaces `C/var.py`'s `seren_client` and `seren_secret` literals in Seren's Trakt source. Neither literal occurs in the supplied Seren source. A dry-run replacement left the entire file unchanged.

Seren actually obtains its client identity from `trakt.clientid` and `trakt.secret`, with different built-in fallbacks. ReAuthorize's Seren block writes `trakt.auth`, username, refresh and expiry, but not those client settings. Thus a default installation receives ReAuthorize's token with Seren's own application identity. An existing custom client setting would also override a successful fallback patch.

Fix: write the explicit `trakt.clientid` and `trakt.secret` settings with the matching credential bundle. Verify them even when the access token already matches. Avoid modifying Seren source for this version.

Evidence: `R/sync/trakt_sync.py:36–65`; `C/var.py:371–372`; `P/plugin.video.seren/resources/lib/indexers/trakt.py`, `_load_settings()` around lines 557–570.

### F03 — TMDb Helper receives a Trakt expiry 90 days too late (high)

ReAuthorize writes a JSON token with `created_at = trakt.expires` and `expires_in = 7776000`. TMDb Helper calculates expiry as `created_at + expires_in`. ReAuthorize has supplied the expiry as if it were the creation time, then added 90 days.

This is a confirmed timestamp encoding defect. It can mislead expiry/status/refresh decisions; the precise failure recovery after an HTTP refusal depends on TMDb Helper's runtime path.

Fix: use the actual recorded lifetime and `created_at = expires_at - lifetime`, or retain the provider's original token timestamps. Use `json.dumps`, not manual JSON concatenation. Compare refresh token and timestamps as well as access token.

Evidence: `R/sync/trakt_sync.py:607–630`; `P/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/api/trakt/token.py:63–100`. Unlike Seren, the supplied TMDb Helper's key file does contain the literals ReAuthorize tries to patch; the confirmed defect here is the timestamp construction.

### F04 — Umbrella FilePursuit is written to the wrong setting (high)

ReAuthorize writes `filepursuit.api`; Umbrella's active scraper reads `filepursuittoken`. Umbrella's source selection also checks `filepursuittoken`. A dummy-data test confirmed sync wrote the unused setting while leaving the real reader credential unchanged.

Fix: update writer, importer and removal mappings to `filepursuittoken`; preserve `filepursuit.enable` as appropriate. Verify the key against the active scraper, not just settings labels.

Evidence: `R/sync/filepursuit_sync.py:18–30`; `P/plugin.video.umbrella/resources/lib/internal_scrapers/filepursuit.py:31–33`; `resources/lib/modules/sources.py:1873`. Inspect the importer too: its Umbrella mapping still contains the obsolete FilePursuit name.

### F05 — POV metadata writes target obsolete/unused fields (medium)

ReAuthorize writes `tmdb_api` and `fanart_client_key`. POV's supplied TMDb API reads `tmdb_read_token` and sends `Authorization: Bearer ...`. No active Python reader for `fanart_client_key` was found in this POV version.

A v3 API key must not simply be copied into `tmdb_read_token`: they are different credential types. The current block also does not transfer POV's supported TMDb account-session fields.

Fix: remove stale claims/mappings. If supporting POV TMDb metadata, collect an appropriate read-access token and map it separately. If supporting account lists, investigate `tmdb.session_id`, `tmdb.session_account_id`, `tmdb.account_id`, and the account authentication code as a separate integration.

Evidence: `R/sync/meta_sync.py:127–142`; `P/plugin.video.pov/resources/lib/indexers/tmdb_api.py:11–24`; POV `resources/settings.xml`.

### F06 — EasyDebrid is not an active playback target in supplied POV/Umbrella (medium)

ReAuthorize writes `ed.token`, `ed.account_id`, `ed.enabled` to POV. None is present in the supplied POV settings schema or Python service implementation. Umbrella contains an EasyDebrid implementation and settings, but its resolver registration explicitly comments out the enable check and resolver append.

User impact: saved credentials and a green sync status do not make these supplied versions use EasyDebrid. This is an unsupported/disabled receiver capability, not a password failure.

Fix: version/capability checks and an honest unsupported status. Re-enabling a receiving plugin's resolver is a separate plugin change and requires its own validation.

Evidence: `R/sync/easydebrid_sync.py`; `P/plugin.video.umbrella/resources/lib/modules/debrid.py:15–33`; supplied POV settings and indexers.

### F07 — Seren gained services that ReAuthorize does not send (medium)

The supplied Seren has TorBox (`torbox.token`), OffCloud (`offcloud.apikey`) and Debrid-Link (`debridlink.token`, with OAuth refresh/expiry fields) implementations. ReAuthorize's TorBox and OffCloud sync files contain no Seren target. Its Debrid-Link sender deliberately does nothing, based on a comment that its only former target was retired Salts.

Seren also has MDBList API-key support using `mdblist.apikey` and username; ReAuthorize's Seren metadata block never sends it. Easynews is exposed as a provider toggle, but its actual credentials may belong to an external provider package; no direct credential integration can be established from the supplied Seren files alone.

Fix: implement and test the missing service adapters. For Debrid-Link, determine whether ReAuthorize's manually entered key is accepted by this consumer, rather than assuming it is interchangeable with Seren's OAuth token. Send the relevant enable flags and clear credentials on removal. Update “supported services” displays.

Evidence: `R/sync/torbox_sync.py`, `offcloud_sync.py`, `debridlink_sync.py`, `meta_sync.py:29–53`; Seren `resources/lib/debrid/{torbox,offcloud,debrid_link}.py` and `resources/lib/indexers/mdblist.py`.

### F08 — Umbrella Trakt issuer marker is not updated (high, conditional)

Umbrella records `trakt.authed.clientid` on its own sign-in. Its renewal path clears the token, refresh and expiry if this nonempty marker differs from the current client ID. ReAuthorize changes the client settings and token but never writes the marker.

Trigger: sign in natively in Umbrella, then replace the sign-in with ReAuthorize's credentials. On a subsequent renewal path the stale marker can make Umbrella remove the newly sent sign-in.

Fix: synchronize `trakt.authed.clientid` to the issuing client and initialize other authentication-state fields consistently with Umbrella's native sign-in. Compare the complete bundle even when the access token matches.

Evidence: `R/sync/trakt_sync.py:115–133`; `P/plugin.video.umbrella/resources/lib/modules/trakt.py:261–274` and its native sign-in around line 352.

### F09 — Revoke does not consistently remove recipient credentials (high)

The Real-Debrid, Premiumize, AllDebrid, TorBox, EasyDebrid, OffCloud and Linksnappy service actions clear ReAuthorize's own values without invoking their receiving-add-on cleanup. Automatic send is mapped to authorization actions, not these revokes. Normal full sync skips a service whose source credential is blank.

Consequently, recipient plugins can stay signed in. TorBox/EasyDebrid also retain source `acct_id` copies containing the API key. The generic `removeService` action has a separate incomplete field list and does not clean recipients; its Last.fm detection still relies on the old session-key field.

Fix: route all removal entry points through one per-service cleanup operation. For ordinary sign-out, clear recipients holding this shared identity; for an explicit full wipe, clear all intended destinations. Remove all duplicates and prevent backup/import logic from restoring removed credentials.

Evidence: `R/auth/{realdebrid,premiumize,alldebrid,torbox,easydebrid,offcloud,linksnappy}.py`, `R/autosend.py:TAG_FOR_ACTION`, and `lib/default.py` corresponding revoke actions and `removeService`.

### F10 — Incomplete comparisons cannot repair credential bundles (medium)

Most older adapters check one access token before writing several required values. If that token is already correct but the client ID, secret, refresh token, account label or enabled flag is missing/wrong, a resync may do nothing. This affects core Real-Debrid/Trakt and other adapters across multiple plugins.

The earlier Easynews reproduction showed a username-only change is skipped when the password is unchanged. This directly applies to supplied POV and Umbrella, which read the username/password fields written in those blocks. The earlier Linksnappy password-only reproduction applies to Cosmos, which was not included here.

Fix: compare and repair every member of a service's credential bundle, with separate rules for user preference toggles. Do not use an access-token equality check as a substitute for validation.

### F11 — Failures and unsupported destinations are reported as success (high)

Inner adapters frequently swallow exceptions; `sync_all._try()` sees normal completion and sets a service flag. Many targets also require a profile `settings.xml` and silently skip a newly installed plugin that has never saved settings. A correct settings mapping is insufficient if this precondition is unmet.

Fix: structured per-addon results; distinguish unsupported, not initialized, already current, written and failed. Verify values after writes and verify a harmless authenticated request only when the service supports one. Show a service as sent only if at least one intended destination was reached. Preserve error detail without logging secrets.

Evidence: `R/sync_all.py`, older `R/sync/*.py` catch blocks, and the `_settings_ready` predicates in the newer OAuth adapters.

### F12 — Shared renewal ownership remains inconsistent (architectural risk)

Trakt and MDBList refresh tokens are sent to multiple independent consumers. ReAuthorize renews early, but there is no common atomic renewal lock spanning all receiving plugins and Kodi instances. Supplied consumers contain their own renewal code. Real-Debrid consumers such as POV also refresh and persist new credentials locally; ReAuthorize does not automatically receive every locally updated bundle before resending its stored values.

Umbrella's MDBList renewal uses its own hard-coded `_CLIENT_ID`, while ReAuthorize sends its OAuth pair without changing that identity. Existing access-token requests use Bearer authentication, so initial requests can work; fallback renewal under the wrong application can fail if ReAuthorize did not renew first. This is a confirmed fallback mismatch, not proof that every initial request fails.

PunchPlay deliberately sends access tokens only, which avoids giving each add-on the refresh token. It remains dependent on successful background renewal and fan-out. Umbrella is given an artificial expiry of 2100; it cannot independently renew the shared token if ReAuthorize is unavailable. ReAuthorize's own PunchPlay window-property busy check/set is not an atomic cross-process lock.

Fix: define one renewal owner per shared sign-in, persist each bundle atomically, and propagate only after commit. Prefer receiving-addon import APIs with identity/expiry handling. Where consumers cannot cooperate, consider separate authorizations or clearly document the dependency.

## Compatibility matrix

Legend: **M** = main credential mapping matches supplied consumer; **B** = confirmed broken/stale mapping or timestamp; **G** = receiving capability exists but ReAuthorize has no appropriate send path; **D** = disabled/absent runtime capability despite sender; **P** = partial evidence/dependency missing; **—** = no reviewed integration for this pair. All M cells remain subject to F09–F12 and are not live-service passes.

| Service | Seren | Crew | TMDb Helper | TMDb Movies | Umbrella | POV | Prism | Red Light |
|---|---|---|---|---|---|---|---|---|
| Trakt | B F02 | M + Crew addendum | B F03 | M | M + F08 | M | — | M |
| Real-Debrid | M | M via ResolveURL + C05/R03 | — | M access token only | M | M | M | M |
| Premiumize | M | M via ResolveURL + C05 | — | M | M | M | M | M |
| AllDebrid | M | M via ResolveURL + C05 | — | — | M | M | M | M |
| TorBox | G | G: ResolveURL mapping missing | — | M | M | M | M | M |
| OffCloud | G | M generic ResolveURL; cache-check limit | — | M | M | M | M | M |
| EasyDebrid | — | — | — | — | D | D | — | — |
| Debrid-Link | G | — | — | — | — | — | — | — |
| Easynews | P external provider | M + F10 | — | P external playback only | M + F10 | M + F10 | — | M |
| FilePursuit | — | P account modules | — | — | B F04 | — | — | — |
| Simkl | — | M + Crew removal issue | — | M | M source patch | — | M fields; API-version risk | M |
| MDBList API key | G | — | M | M | B unused mdblist.api | G: mdblist.token fallback | M | — |
| MDBList OAuth | — | — | — | M | M access; F12 renewal | M | — | M |
| PunchPlay | — | — | — | M access only | M access only | — | — | M access only |
| TMDb metadata key | M | M fallback; personal override wins | — | — | M | B F05 | G: tmdb.apikey override exists | M |
| TMDb personal session | — | — | G different auth format | G different auth format | M session fields | G account fields not sent | — | deliberately omitted |
| Fanart.TV | M | M | M | — | M | B unused field | M | M |
| OMDb | M | — | M | — | — | — | — | M |
| IMDb profile ID | — | M | — | — | M | — | — | — |
| TheAudioDB | — | — | — | — | — | — | — | — |
| Linksnappy | — | — | — | — | — | — | — | — |
| Last.fm | — | — | — | — | — | — | — | — |
| TorrentClaw | — | — | — | — | — | — | — | — |
| YouTube account | — | — | — | — | — | — | — | — |

Notes: The Crew module and ResolveURL are now supplied. RD/PM/AD setting names match; disabled resolvers are not re-enabled by those senders. OffCloud's generic ResolveURL credential mapping also matches, but Crew's dedicated cache-check list includes RD/AD/PM/TorBox, not OffCloud. See both follow-up addenda. A dash does not assert that a plugin can never use that service through an external module. TMDb Movies recognizes Easynews streams in its external playback flow, but no direct Easynews username/password authentication reader was established. Its `aio_password.N` settings belong to the AIO account flow and must not be treated as Easynews password slots. Prism explicitly supports a `tmdb.apikey` override (`resources/lib/database/keys.py`), but ReAuthorize's Prism metadata block writes only Fanart and MDBList.

Red Light is a positive finding: ReAuthorize correctly writes its SQLite settings database rather than only Kodi settings.xml. The supplied `sync_settings` route clears its database cache and reapplies properties even with `load_properties=false` when properties have been loaded. No confirmed database-format or reload-route mismatch was found in this version. An initialized DB is still required; UPDATE-only writes do not create missing rows. Per-row verification remains advisable.

POV's dynamic `%s.enabled`/`%s.token` access means the absence of literal `rd.enabled` or `tb.enabled` strings is not a defect. Its service monitor also refreshes the shared settings property after settings changes. These were checked to avoid false positives from text searches.

## Other service findings retained from the initial archive audit

These apply to ReAuthorize source, but their receiving addons were not supplied here.

| Service | Finding / verification limit |
|---|---|
| Real-Debrid sign-in | `get_token()` returns `(success, error)` but `auth()` tests the whole tuple; `(False, None)` is truthy. False success notification confirmed by return-shape analysis. Some authentication calls lack timeouts; recursive `_post()` retries have no explicit limit. |
| Premiumize | Request helpers can return an unassigned local `response` after a transport exception. Main supplied receivers use Bearer headers, consistent with the sender's token field; live acceptance of a manual API key was not tested. |
| TorBox / EasyDebrid | API key is duplicated into account-ID settings. Do not treat a credential as an account identifier; revoke must clear both copies. |
| FilePursuit | Empty/canceled input is saved and followed by success notification. Validate and preserve previous value on cancel. |
| Linksnappy | Cosmos sync compares username only; password-only changes were reproduced as skipped. Cosmos was not supplied. |
| Last.fm | Sync enables song/video/radio submission unconditionally. Session-key-only legacy revoke clears the scrobbler only if a password exists, leaving that legacy recipient authorized. Scrobbler absent here. |
| TheAudioDB | Key is collected and backed up, loaded by metadata sync, but no outgoing write uses it. No destination integration found. |
| YouTube | Existing complete ReAuthorize API credentials are preserved while a new sign-in file can be captured under different credentials. Restore can combine mismatched credentials/tokens; store them as a verified bundle. Plugin absent here. |
| TorrentClaw | Only Cosmos is a target. Key check and matching-key removal exist; errors can be swallowed and targets require settings.xml. Cosmos absent here. |
| IMDb | Public profile identifier, not an account token. Do not equate writing it with successful account authorization. |

Security: refresh tokens can appear in Real-Debrid debug-file logging. QR URLs are sent to an external QR-rendering provider, potentially including approval codes. Backup encryption is custom XOR-keystream encryption with no authentication tag and a key derived solely from a device ID; the server receives that device ID. This does not provide confidentiality against that server operator or authenticated ciphertext integrity. Prefer a standard authenticated-encryption design with a secret independent of the public identifier. Kodi settings and recipient copies also retain reusable secrets in local storage.

## Validation performed

1. Parsed all 121 ReAuthorize/core Python sources in the earlier pass: no syntax errors.
2. Read addon manifests to establish all eight supplied plugin versions and missing dependencies.
3. Compared sender setting writes with receiving Python readers and settings schemas; followed dynamic access to avoid treating missing literal strings as errors.
4. Dry-run Seren key replacement: neither expected old literal matched; resulting source unchanged.
5. Compared TMDb Helper token construction with its timestamp reader: calculated expiry is 7,776,000 seconds (90 days) later than ReAuthorize's actual stored expiry.
6. Executed isolated Umbrella FilePursuit writer block with dummy settings: `filepursuit.api` changed; real `filepursuittoken` unchanged.
7. Executed isolated POV metadata writer: only obsolete `fanart_client_key`/`tmdb_api` populated, not the active bearer-token setting.
8. Executed isolated Umbrella metadata writer with only a Fanart source: existing TMDb key and session cleared.
9. Verified Umbrella's issuer-mismatch deletion guard and absence of its issuer marker from ReAuthorize's Trakt writes.
10. Verified lack of Seren targets in TorBox/OffCloud sync, no-op Debrid-Link sync, and absent Seren MDBList key write.
11. Earlier dummy-data checks reproduced Easynews username-only and Linksnappy password-only update failures, and silent skipping when profile settings.xml is absent.

Seven targeted second-pass assertions passed. They are a mixture of isolated writer execution, source invariants and timestamp arithmetic, not seven end-to-end Kodi tests. No provider API requests, credential refreshes, logins, source patches, settings writes to a real Kodi profile, or playback tests were performed.

## Recommended repair sequence

1. Stop blank metadata propagation and centralize targeted sign-out; test preservation of unrelated credentials.
2. Repair Seren Trakt, TMDb Helper expiry and Umbrella issuer marker. Test initial import, native-sign-in replacement, resync of a partially damaged bundle, expiration and renewal.
3. Correct FilePursuit's Umbrella writer/importer/removal field; remove obsolete POV metadata/EasyDebrid claims.
4. Add explicit versioned adapters for newly supported Seren services, Seren MDBList and Prism TMDb metadata. Keep API keys, read tokens and user sessions separate.
5. Return structured results from every adapter; initialize supported targets or explain why they were skipped; verify complete bundles.
6. Coordinate token renewal and persistence; replace fragile source edits with supported setting/import interfaces where available.
7. Run a Kodi test profile with dummy or dedicated test accounts across initial install, existing native authorization, changed credentials, plugin update, background renewal, sign-out, backup/restore and full wipe.

Additional source needed for the remaining integrations: any account-manager dependencies actually used, `context.prism`, the relevant scrobblers, YouTube, and any other target plugins the user wants certified. A full Kodi profile is unnecessary; sanitized addon source zips and dependencies are sufficient.


## Follow-up: The Crew module 3.2.26

The third uploaded archive closes the missing implementation gap for The Crew. Sources below use `K/` for `plugin_audit/script.module.thecrew/lib/resources/lib/`. No source was patched during this audit. Trakt application identifiers and the corresponding source marker were already present in the upload; they are application-level values, not evidence of an uploaded personal access token.

### What now matches

- Trakt: `trakt.user`, `trakt.token`, `trakt.refresh`, `trakt.expires_at`, and `trakt.revoked=false` match the current consumer. ReAuthorize's Crew-specific adapter repairs the whole listed bundle and clears revoked/auth-failure window flags, unlike several older adapters. The supplied application's keys match ReAuthorize's application identity.
- Simkl: `simkl.token`, `simkl.user`, and `simkl.client_id` are read by both the module and API wrapper; the override wins over Crew's built-in client identity.
- Easynews: `easynews.user` and `easynews.password` match the scraper. F10's password-only comparison still prevents a username-only update.
- Fanart and IMDb: `fanart.tv.user` and `imdb.user` have active consumers. The earlier UI-only uncertainty is resolved.
- TMDb: `tm.user` is read, but `tm.personal_user` takes precedence. An existing personal override therefore prevents ReAuthorize's newly sent fallback key from taking effect. This should be reported as an existing user override rather than silently declared synced to the active key.
- Debrid: RD/PM/AD consumer fields use ResolveURL, consistent with the principal names written by ReAuthorize. ResolveURL's implementation itself was not supplied, so this is field/path verification, not an end-to-end resolver pass.

### C01 — Trakt key setup failure is ignored (high, conditional)

`R/sync/crew_trakt.py:link()` calls `ensure_key()` but ignores its result. A read-only/missing/moved Trakt source file can therefore leave the old application identity while new tokens are still written. An isolated test forced `ensure_key()` to return False and confirmed `link()` nevertheless wrote the new token and reported a change.

Fix: verify both effective client values before writing a shared token. Return a failure if identity cannot be established. Avoid using mere presence of the client text anywhere in the source as proof both key lines are correct. The current upload is already correctly patched, so this is a conditional failure path rather than a current identity mismatch.

### C02 — Already marked Trakt keys cannot be updated (medium)

`swap_key()` leaves a line unchanged whenever it contains `# ReAuthorize; was:`, even if its value differs from the newly requested identity. On the supplied marked source, a dummy request for different client/secret values changed nothing. This matters after application-key rotation or importing an older patched installation; it is not a current mismatch in this upload.

Fix: compare the actual assigned value; update it while preserving the original restore marker. Validate the result structurally.

### C03 — Backup XML values are not escaped (medium)

`_set_in_xml()` substitutes values directly into XML text. With dummy account text `A & B`, the resulting settings backup failed XML parsing. '<' has the same class of problem. Provider acceptance of such account names is not assumed; the serializer is unsafe for general setting values regardless.

Fix: use ElementTree or XML escaping and atomic writes; parse the completed backup before replacing it. Restrict this test to dummy values, never real credentials.

### C04 — Simkl sign-out can be undone by Crew's recovery copy (high)

ReAuthorize's Simkl sign-out clears Crew's live Simkl settings through `simkl_sync.sign_out_addons()`, but does not invoke Crew's backup cleanup. Crew includes Simkl user/token/client in `_SENSITIVE_SETTING_IDS` and fills empty sensitive values from its profile backup. Its special no-restore guard applies to Trakt revocation, not to Simkl. Crew's own native revoke explicitly calls `purge_simkl_credentials_from_backups()`; ReAuthorize bypasses it.

Trigger: a previously saved Crew recovery copy contains the Simkl sign-in; remove Simkl through ReAuthorize; Crew later runs recovery. The old sign-in can return. This is established by the source control flow, not a live Kodi reproduction.

Fix: route through a supported Crew credential-removal operation, or clear all relevant recovery copies and persist an intentional sign-out marker before recovery can run. Synchronize replacement Simkl tokens/client identity into those copies as well. Relevant sources: `R/sync/simkl_sync.py`; `K/modules/simkl.py:revoke_simkl`; `K/modules/settings_repair.py:593–614`, `695–713`, and `968–982`.

### C05 — Debrid token writes do not enable disabled resolvers (medium)

Crew's `_get_debrid_enabled()` requires BOTH `<Resolver>_enabled == 'true'` and a nonempty credential. ReAuthorize's RD/PM/AD ResolveURL blocks write tokens (and associated fields) and `cached_only`, but not their `_enabled` fields. A deliberately disabled resolver therefore stays inactive after sync even with valid credentials.

This is a conditional capability/state mismatch, not proof default installations fail: ResolveURL defaults were not supplied. Fix: define whether explicit authorization should enable a disabled resolver; apply that policy and report the state. Do not silently change a deliberate preference during routine background renewal.

Evidence: `K/modules/debridcheck.py:37–49`; `R/sync/debrid_rd.py:635–646`, `debrid_pm.py:574–581`, `debrid_ad.py:556–564`.

### C06 — TorBox is not sent to The Crew's actual resolver (medium)

Crew's active cache-check code reads `TorBoxResolver_apikey` and `TorBoxResolver_enabled` from `script.module.resolveurl`. ReAuthorize's TorBox sender has no ResolveURL target at all. Sending TorBox to other video plugins does not configure Crew's resolver.

Fix: add a version-tested ResolveURL TorBox adapter with key/enabled handling and cleanup, after inspecting the actual ResolveURL package. Evidence: `K/modules/debridcheck.py:48`, `296`; `R/sync/torbox_sync.py`.

### Operational behavior: only one tracker is active

Crew uses `tracker.service`: 0 = Trakt, 1 = Simkl. Its Trakt credential-info function returns False when Simkl is selected even if Trakt credentials exist. ReAuthorize does not change this selection when sending either account. Preserving the user's selection is reasonable, but status must distinguish “credentials stored” from “active tracker.” This explains a class of apparent authorization failures without implying a bad token.

Evidence: `K/modules/simkl.py:get_tracker_service`; `K/modules/trakt.py:2441–2454`.

### Backup and renewal limits

ReAuthorize's backup discovery agrees with this module's current external backup path calculation: both use the parent of translated `special://home`, plus the legacy profile path. There is no confirmed path disagreement in these supplied versions, despite the confusing root descriptions in comments.

Crew's own backup iterator additionally considers legacy `settings*.bak` files. ReAuthorize considers only `settings.xml.bak` plus `settings.xml.health_backup_*` and its two known external locations. Additional legacy copies can therefore remain unsanitized by ReAuthorize's wipe. Prefer Crew's own supported backup-purge routine, with ownership-aware cleanup.

Crew independently refreshes Trakt and can adopt differing tokens from a Classy sibling after checking usernames but without checking their issuing client identity or freshness. ReAuthorize's source-key patch changes the usual shared-client assumption behind that adoption. If Classy is installed and holds a different app's token, adoption can create a wrong-client refresh path. Classy was not supplied, so this is a conditional integration risk, not a confirmed failure of this upload alone.

### Follow-up validation

Three isolated assertions passed: marked source ignores replacement identity; unescaped account text creates invalid backup XML; and token writes proceed after key setup fails. Consumer readers, native removal paths, recovery merging, dynamic resolver gates, tracker selection, and current backup-path calculations were reviewed directly. No API calls, real settings writes or source mutations were performed. ResolveURL is the principal remaining source needed to finish The Crew's debrid side.


## Final follow-up: ResolveURL 5.1.211

The fourth upload establishes the real resolver side of the Crew integrations. Use `U/` for `plugin_audit/script.module.resolveurl/lib/resolveurl/` below. Earlier references to ResolveURL being missing describe the previous audit stage; the findings in this addendum supersede that limitation. No resolver source or Kodi settings were modified.

### Verified service mappings

ResolveURL prefixes every plugin setting with the resolver class name and an underscore (`U/resolver.py:167–172`). These are actual runtime names, not guesses from labels.

| Service | Actual ResolveURL credentials | ReAuthorize result |
|---|---|---|
| Real-Debrid | `RealDebridResolver_token`, `_refresh`, `_client_id`, `_client_secret` | Names match. Sender additionally writes `_login` with the RD username, but this is a legacy boolean login flag rather than an account-name field; the RD override's active gate is enabled + token, so this extra write is not established as the cause of failures. |
| Premiumize | `PremiumizeMeResolver_token` | Matches; consumer sends Bearer authentication. |
| AllDebrid | `AllDebridResolver_token` | Matches; consumer sends Bearer authentication. Sender's `_client_id` username write has no active consumer in the supplied AllDebrid resolver. |
| OffCloud | `OffCloudResolver_apikey` | Matches; sender also enables resolver when its token-write block runs. Consumer sends Bearer authentication. |
| TorBox | `TorBoxResolver_apikey` | No ResolveURL target in ReAuthorize's TorBox sender. Missing integration confirmed. |
| Linksnappy | `LinkSnappyResolver_username`, `_password`, plus an authenticated cookie file and `_expiration_timestamp` | No ResolveURL target in ReAuthorize's Linksnappy sender. Credentials alone would not complete its active-state requirements. |
| Debrid-Link / EasyDebrid | No corresponding resolver found in this supplied package | Do not invent mappings or report these as supported ResolveURL destinations. |

### R01 — Resolver enable-state behavior is now fully confirmed

RD, Premiumize, AllDebrid, OffCloud and TorBox each override `_is_enabled()` to require both `enabled == 'true'` and a credential. An isolated execution of each real gate returned False with a dummy credential and a disabled flag.

The base settings generator defaults `enabled` to true (`U/resolver.py:160`), so the earlier Crew C05 issue is specifically an already-disabled or otherwise false-enabled-state case, not evidence that untouched default installations fail. ReAuthorize's RD/PM/AD senders do not repair that state. OffCloud does set enabled to true, but only inside its credential comparison block; if the key already matches and enabled is false, a resync still does nothing. This is another example of F10's incomplete bundle comparison.

### R02 — TorBox integration missing; Linksnappy needs cookie authentication

Crew's TorBox path reads exactly the same `TorBoxResolver_apikey` name now verified in the resolver, closing the remaining uncertainty in C06. ReAuthorize never writes it through its TorBox sender, and its ResolveURL import mapping lacks this credential too.

ResolveURL also supports Linksnappy, but ReAuthorize sends that service only to Cosmos. `LinkSnappyResolver._is_enabled()` requires enabled plus the cookie file. `authorize_resolver()` uses username/password to obtain and save that cookie and update an expiration timestamp. A future integration must invoke/implement the authentication lifecycle, invalidate old cookies when changing accounts, and remove cookies on sign-out; just adding two setSetting calls is insufficient.

Evidence: `U/plugins/torbox.py:47–48`, `468–469`; `U/plugins/linksnappy.py:550–593`; `R/sync/{torbox_sync,linksnappy_sync}.py` and `R/import_map.py`.

### R03 — A temporary Real-Debrid refresh failure deletes authorization (high)

`RealDebridResolver.__get_token()` catches any exception and returns False. This includes transport failures, malformed/HTML responses, and missing expected JSON fields. `refresh_token()` treats any False as grounds to call `reset_authorization()`, erasing client ID, secret, access token and refresh token, then raising an error.

A dummy-data execution of the real refresh control flow confirmed that a failed exchange invokes reset. No actual network request was made. This failure policy belongs to ResolveURL rather than ReAuthorize, but directly explains The Crew unexpectedly losing a shared Real-Debrid login during renewal. ReAuthorize may retain its own copy while the receiving resolver is now blank.

Fix: distinguish definitive invalid/revoked credentials from temporary errors. Preserve the current bundle on timeout, HTTP 5xx, rate limits or unreadable response. Commit replacement credentials only after validating the complete successful response. Keep credentials intact on a retryable failure.

Evidence: `U/plugins/realdebrid.py:270–278`, `297–310`, `322–326`.

### R04 — Shared Real-Debrid refresh state can diverge

ResolveURL refreshes and stores the new RD token/refresh pair in its own settings. ReAuthorize has a separate stored copy and other add-ons have their own copies. These writes are not fed back atomically to ReAuthorize's vault or other consumers. A subsequent push can send the older pair again. The source establishes the divergent storage and renewal paths; whether an old refresh credential is accepted depends on provider behavior and was not tested here.

Fix: a coordinated renewal owner with a transactional credential bundle, or an explicit adoption rule that validates identity and freshness before resending. Avoid treating one token string as the entire service state.

### R05 — Receiving resolver state persists after ReAuthorize-only removal

ResolveURL has explicit native reset paths for RD, Premiumize, AllDebrid, TorBox, OffCloud and Linksnappy. ReAuthorize's standard RD/PM/AD/OffCloud revoke actions do not call those reset paths or otherwise clear recipient settings (F09). These are usable independent credential copies until removed or invalidated by the provider. For Linksnappy, future cleanup must also remove cookies. Local removal is distinct from revoking a provider-issued token remotely.

### R06 — ResolveURL logs reusable Real-Debrid credentials (security)

The RD resolver debug-logs the refresh token and the entire token-exchange JSON response, which contains access/refresh tokens on success. Log sharing can disclose a working authorization. This is additional to ReAuthorize's own debug logging issue; do not assume sanitizing one logger sanitizes the other.

Evidence: `U/plugins/realdebrid.py:274`, `305–307`. Fix: log only status codes and nonsecret correlation information. Never emit raw tokens or full authentication responses. Existing shared logs should be treated according to their actual contents; this audit did not inspect personal logs.

### Crew-specific capability limit

Crew's generic resolver enumeration can use universal ResolveURL resolvers, including OffCloud when enabled. Its dedicated cache-check list in `K/modules/debridcheck.py:_get_debrid_enabled()` contains RD, AD, Premiumize and TorBox only. Therefore correct OffCloud authorization does not imply identical torrent/cache-check support to those four services. No unsupported cache feature should be presented as an authentication failure.

### Final validation and remaining scope

Six isolated follow-up assertions passed: RD refresh failure invokes reset; and each of the five RD/PM/AD/OC/TB gates stays inactive with a credential while disabled. Namespacing, Bearer headers, native authentication/reset paths, TorBox/Linksnappy omissions, cookie dependency, defaults and debug logging were inspected directly.

The Crew module/ResolveURL source dependency gap is now closed. This remains a source and dummy-data audit, not a live Kodi or provider acceptance test. The separate missing plugins/scrobblers listed above still limit conclusions about their integrations. Recommended next step is to repair ReAuthorize's confirmed sender defects, then validate in an isolated Kodi profile with controlled accounts; this audit did not change any plugin package.
