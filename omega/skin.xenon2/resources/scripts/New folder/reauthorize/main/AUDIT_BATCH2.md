# addons2.zip follow-up inventory and findings

| Addon | Supplied version |
|---|---|
| context.otaku | 1.0.35 |
| plugin.video.absolution | 4.4.1 |
| plugin.video.aliundek19 | 0.3.9 |
| plugin.video.base | 1.4 |
| plugin.video.blacklightning | 2.4.2 |
| plugin.video.blueballs | 1.9 |
| plugin.video.genocide | 6.9.9 |
| plugin.video.ghost | 1.6.6 |
| plugin.video.homelander | 1.3.1 |
| plugin.video.moria | 4.11.10 |
| plugin.video.nightwing | 1.1.7h |
| plugin.video.otaku | 5.3.4 |
| plugin.video.quicksilver | 0.3.7 |
| plugin.video.scrubsv2 | 5.1.42 |
| plugin.video.shadow | 3.8.1 |
| plugin.video.thearchives | 1.2.3.3 |
| plugin.video.thechains | 6.0.1 |
| plugin.video.torquelite | 10.5 |
| plugin.video.twisted | 2.2 |
| script.absolution.artwork | 4.1.7 |
| script.homelander.artwork | 1.0.4 |
| script.module.absolutionscrapers | 4.0.5 |
| script.module.chainscrapers | 1.0.8 |
| script.module.cocoscrapers | 1.0.44 |
| script.module.homelanderscrapers | 2.0.4 |
| script.module.moriascrapers | 1.03.05 |
| script.module.nightwingscrapers | 1.0.4b |
| script.module.orion | 5.1.7 |
| script.module.quicksilverscrapers | 0.0.6 |
| script.moria.artwork | 1.1.0 |
| script.quicksilver.artwork | 0.0.6 |
| script.simkl | 3.2.4 |
| service.mdblist-scrobbler | 1.3.14 |

## Findings specific to this batch

- Homelander, Quicksilver, Absolution and Moria support explicit Trakt client settings; the patch uses them. Moria was treated as retired by the original sending list but the supplied 4.11.10 source has usable settings overrides.
- Chain Reaction's fallback secret differs from the literal expected by the original core mapping. Its explicit client settings avoid that mismatch.
- Correction to an intermediate commentary: Genocide's original sender uses var.genocide_client/secret, not nonexistent var.newgenocide_client/secret; those literals match its current source. The unused trakt.client_id/secret setting writes do not replace its actual source-key patch.
- Shadow, Ghost, Blue Balls, Twisted, Base, Black Lightning, Aliunde K19 and Scrubs V2 contain the legacy literals searched by their original source-key swaps. Their token fields generally match. This does not prevent custom overrides, stale in-memory source, independent refreshes or source-file permission failures.
- Nightwing's live credential fields match the written Trakt fields; receiving service behavior still needs Kodi validation.
- The Archives uses hard-coded Trakt identity through util/dev_api.py; writing hypothetical client-id settings does not override it. It has valid dynamic pm/ad token readers, so lack of literal pm.token/ad.token in Python is not proof those fields are unsupported. Its unused duplicate aliases are removed in the patch, while its declared/dynamic fields remain.
- Otaku 5.3.4 simkl.login is a settings action. Its real Simkl credential fields are separate, and client identity comes from a shared database. ReAuthorize must not place a token in the action field; a complete compatible adapter remains outstanding.
- Simkl scrobbler 3.2.4 reads APIKEY from resources/lib/api_simkl.py and its token setting. The existing source-key adapter recognizes that line.
- MDBList scrobbler 1.3.14 reads oauth_tokens.json with access_token/refresh_token/expires_at, and MDBLIST_CLIENT_ID in resources/lib/oauth.py. These agree with the existing adapter. Shared refresh ownership remains unresolved.
- Scraper and artwork dependencies were inspected for their routing role. They are not automatically independent authorization destinations, and no invented service-setting mappings were added to them.

Scope: static consumer/schema/source-identity checks, followed by dummy-data patch regressions. The supplied packages were not executed. Not every feature in these plugins is part of this authorization audit.
