# Kodi Favourites Sync v0.3.16 (two-way household sync)

This Kodi service add-on merges `special://profile/favourites.xml` across Kodi
installations paired to **the same Google account**. It retains the existing browser-based Google Drive authorization bridge.

**Pairing window:** QR-code pairing is the default, generated locally with
Kodi's `script.module.qrcode` dependency. The custom pairing window displays a
scannable activation link and countdown. A skin-native text-only option is
available through the **Use text-only pairing window (no QR)** setting.

## Install and set up

1. Make a copy of your existing `userdata/favourites.xml` on every Kodi device.
2. **Upgrade every Kodi device** to v0.3.16 to use these optimizations.
   Versions before v0.3.0 use a single shared `favourites.xml` cloud file and
   do not understand the multi-device journal protocol.
3. Install the ZIP using Kodi's *Install from zip file*, then restart Kodi to
   start the newly enabled background service.
4. On each device, open add-on settings and select **Pair Google Drive now**.
   Pair every device to the **same Google account** using the existing bridge.
5. Pairing now automatically attempts the first merge, even if the device has
   never created its own `favourites.xml`. The first sync **unions** existing
   favourites; missing favourites do not count as deletions.
6. The add-on now syncs quietly at Kodi startup and periodically while it is
   running. Pairing and **Sync favourites now** never force a profile reload; a first import or manual download may offer to close and reopen Kodi.
7. Kodi already loads its in-memory favourites before startup service add-ons
   run. If newly downloaded entries do not appear immediately, they will be
   available after the next normal Kodi launch. When the sync succeeds,
   its XML updates stay saved between launches.

## How two-way synchronization works

- Each installation has a persistent random device ID and its own append-only
  Google Drive journal in the app's hidden **appDataFolder**. Multiple devices
  do not overwrite the same remote XML file or each other's journal.
- On the first sync, the app combines each device's existing favourites with
  those already present in the cloud. If no new journals exist, the old remote
  `favourites.xml` from v0.2.36 is imported too. The old file is left in place.
- Subsequently, the app compares the local file to the last successfully
  applied local snapshot. It tracks *additions, deletions and thumbnail edits*
  as device-specific events, then merges all events. It does not rely on device
  clocks or remote modification timestamps for conflict resolution.
- Deletions remove only the known copies of that entry (*observed-remove set*).
  Thus, if devices independently add the same entry concurrently, a concurrent
  deletion may not remove the other add; the entry may briefly reappear. A
  later deletion after everyone has synchronized will remove all known copies.
- Exact matches by **name + Kodi launch action** are considered duplicates.
  Same name with different Kodi actions are retained as distinct favourites,
  and same action with different labels is also retained. The original local
  ordering is kept per device; newly downloaded entries are appended.
- Recognized Kodi-local thumbnail paths and safe quoted filesystem paths in
  favourites actions are converted to `special://` references during sync.
  Existing cloud entries with recognizable older Windows/Android paths are
  migrated through normal add/remove events to prevent duplicate favourites.
- URLs, network shares, external media locations, plugin query parameters, and
  paths not confidently identified as Kodi folders are preserved unchanged.
  The add-on does not move or synchronize image files themselves; a local
  `special://` thumbnail only works where the file is installed or cached.
  Device-specific library IDs and missing add-ons may still be unusable.

## Portable favourite paths (v0.3.13)

On the next successful sync, references under known Kodi install, add-on and
userdata directories are normalized to Kodi's `special://` URIs before being
shared. For example, the same add-on icon stored at a Windows path under
`AppData\Roaming\Kodi\addons` or at an Android path under `.kodi/addons`
becomes `special://home/addons/<addon-id>/icon.png`. A userdata image maps to
`special://masterprofile/...`, and supported cached paths can map to
`special://thumbnails/...`.

For already-shared favourites, the add-on performs a one-time migration using
its existing two-way deletion-tracking events, leaving other devices' journal
histories untouched. Local `favourites.xml` is backed up before replacement.

These rewrites happen during a sync, not the instant Kodi's own Add Favourite
command runs. **Upgrade every device** to keep normalization consistent.

**Special paths do not transfer image bytes.** If a custom thumbnail exists
only on one Kodi device, copy that image to the corresponding Kodi location on
the other devices or use a network/HTTPS image URL. External local files and
network URLs cannot be safely converted and are left unchanged.

## Background synchronization

Settings contain:

- **Pair Google Drive now**
- **QR pairing** by default; optional skin-native text dialog
- **Sync on Kodi startup** (enabled by default)
- **Automatically sync while Kodi is running** (enabled by default)
- **Sync interval**: 1, 5 (default), 15 or 30 minutes
- **Sync favourites now**
- **Show last sync status**
- **Refresh displayed favourites (reload Kodi profile)**: optional manual action only; never run or requested by a sync

Changes are made to the local XML file when the service detects new remote
entries. **Kodi may continue showing an old in-memory list until restart**.
The add-on protects recently imported favourites from accidental deletion if
an old Kodi in-memory list rewrites the XML before the profile is reloaded. As a result,
removing newly imported favourites might not propagate until the active Kodi
profile has been reloaded with the merged list. This safety behavior is intentional.

## Data safety

- XML and journal contents are validated before use. Invalid data aborts the
  sync instead of overwriting a valid favourites list.
- Every replacement of an existing local XML file first creates a copy in
  `userdata/addon_data/service.kodi.favourites.sync/favourites-sync-backups/`.
  Up to the latest 10 copies are retained.
- Writes use a temporary file and atomic replacement in the same folder.
- Missing local XML is *never* considered a request to delete all favourites.
- Local events are saved before a cloud upload, allowing a later retry after a
  network failure. A simple lock prevents overlapping manual/background syncs.
- Each device's original `favourites.xml` is not changed until Drive has
  accepted that device's journal update.
- The old cloud `favourites.xml` is **not** updated by v0.3.0; do not run an
  older v0.2.x copy on another device and expect it to join the new collection.
- Never copy this add-on's entire `addon_data` directory between devices:
  doing so also clones the unique device ID and its journal identity.

## Limitations and compatibility

- Kodi 19+ / Python 3, following the original add-on dependency requirement.
- The existing third-party Google authorization bridge
  (`https://auth-bridge-rho.vercel.app`) is unchanged. Its uptime and security
  cannot be established from this add-on's source alone.
- The service never initiates Kodi profile or skin reloads. It also never
  prompts for a reload after pairing or a manual sync. The separate profile
  reload action remains available for explicit user control only.
- Kodi's startup service runs after Kodi has loaded the profile, so the add-on
  cannot guarantee that XML newly downloaded on that same start is immediately
  reflected in Kodi's in-memory favourites. A normal subsequent launch loads it.
- Each device journal grows with the number of historical edits. Large numbers
  of changes may eventually require a future safe journal-compaction protocol.
- Re-pairing Google Drive with a different Google account creates a separate
  cloud collection. Existing local favourites are retained and merged into it.
- Simultaneous conflicting actions use add-wins set semantics, not a globally
  enforced latest-change-wins ordering.

## OAuth and storage

The original OAuth browser pairing flow is retained. The add-on requests
`drive.appdata` scope. The bridge holds the OAuth client secret; Kodi saves
its device tokens to a verified local add-on userdata file (with a read-only
legacy Kodi settings fallback). Tokens are not written to Google Drive journals.

The new cloud journals are named `kodi-favourites-v2-<device-id>.json`. The
legacy `favourites.xml` file may remain in Google Drive appDataFolder for
migration and rollback but **is not a live synced copy** anymore.

## Testing

Merge logic has been tested with simulated multi-device Google Drive sessions,
including initial union, offline additions/deletions, old cloud-file migration,
corrupt downloads, duplicate journal detection, missing files, upload failures
and restart protection. **It has not yet been exercised on real Kodi devices
with the live OAuth bridge or Google Drive service.**


## Pairing window (v0.3.2)

The **QR code** window is the default on new installations. Select **Skin-native**
under *Pairing window style* for a standard Kodi progress dialog without a QR image.
The QR code is now generated fully offline on your device, rather than by a
third-party image website. Kodi only needs an internet connection for the
Google Drive OAuth bridge itself. Existing saved window-style choices are
preserved when updating. If the QR window cannot start, the add-on logs the
reason in Kodi's log and falls back to the skin-native progress dialog.

The bundled QR encoder comes from `python-qrcode` under its BSD license; see
`resources/lib/_qrencode/LICENSE`.


### v0.3.3 compatibility fix
Kodi 21 installations using Python 3.8 could crash on an import-time type alias in the bundled QR encoder. QR now uses Python 3.8-compatible typing aliases, is lazy-loaded, and pairing and sync interval enums are read using Kodi getSettingInt. QR remains the default.


### v0.3.4 QR display reliability
QR is always the default, including on upgrades with an old stored style=0. To opt out, enable the new "Use text-only pairing window (no QR)" setting. If custom skin XML cannot load, the add-on attempts a self-contained Kodi WindowDialog that shows the same offline-generated QR. An actual encoder/window error is reported in the text fallback and kodi.log instead of silently switching dialogs.


### v0.3.5 QR compatibility
Kodi 21 can ship with Python 3.8. The previously bundled QRCode 8.x library was not compatible with that runtime even after partial typing fixes. Version 0.3.5 replaces it with Kodi's `script.module.qrcode` (6.1.0 or newer), declared as an add-on dependency. Kodi's installed module provides the same QR matrix API. The add-on continues to render the PNG itself without requiring PIL or an outside QR website. QR pairing remains the default.


### v0.3.6 pairing display cleanup
The QR pairing dialog now shows only the remaining countdown below the URL. The pairing code is already included in the displayed activation URL and QR image; both QR dialog implementations use the cleaner layout.


### v0.3.8: Empty-profile and first-pairing improvements

Kodi does not normally create `userdata/favourites.xml` until the first
favourite is added. The sync engine treats a missing file as an empty local
collection and creates a valid `favourites.xml` when cloud entries exist. The
absence of a local XML file never means "delete all cloud favourites".

Pairing now immediately attempts an initial cloud merge using the current add-on
settings instance, rather than requiring a separate Sync Now action. If the
first sync cannot complete, pairing is still successful and an error message
explains that the sync should be retried.

Kodi caches favourites in memory, so a successful disk merge may not immediately
show in Kodi's menu. Since v0.3.10, pairing and Sync Now never ask to reload the
profile, and background synchronizations do not interrupt playback. Newly
imported favourites may only appear after a normal subsequent Kodi launch.
The standalone **Refresh displayed favourites (reload Kodi profile)** option
is still available for explicit use if desired. Back up favourites before
testing on a new device.


### Credential storage in v0.3.9

Google Drive authorization is saved in the add-on's local userdata folder as
`google-drive-credentials.json`, using an atomic replacement and restricted file
permissions where supported. Kodi 22 on some Android devices rejects writes to
old add-on settings fields without throwing an exception. Existing credentials
in Kodi settings are still read if the new file does not exist. **This local
file contains OAuth secrets in plain text, similar to Kodi settings, and must
not be shared or included in exported diagnostic archives.** The file is never
uploaded in the favourites sync journals. If an existing pairing failed to
save in v0.3.8, authorize the Shield again once with v0.3.9.


### v0.3.10: Quiet startup sync (no reload prompt)

Kodi's startup service executes *after* the active profile has loaded its
favourites into memory. As a result, it is not possible for this Python service
to guarantee that favourites fetched during that same startup become visible
without a Kodi core refresh. **The add-on never triggers a profile reload or
asks you to reload after pairing or manual Sync Now.** It still syncs on startup
and at the configured background interval. The XML remains safely updated on
disk, ready for Kodi to load at its next normal start. Background merges do not
show unsolicited toast notifications; **Show last sync status** reports results.

### First-time imports and Kodi restarts

When a device first imports favourites from Google Drive, the add-on offers a
one-time **Close Kodi** confirmation on every platform, including Android TV,
Shield, Windows, Linux and macOS. Choose **Close Kodi** to perform a normal Kodi
shutdown, then reopen Kodi using your usual launcher. Kodi reads the imported
`favourites.xml` on that next launch. Choose **Later** to keep Kodi running;
the favourites remain saved to disk until you next exit and reopen Kodi.
Routine synchronization never shows this prompt, and the add-on does not
force-stop Kodi or automatically reload the active profile.


### Manual Sync Now feedback (v0.3.14)

Manual **Sync favourites now** displays a small background activity indicator, then either a sync error, an up-to-date confirmation, or a **Close Kodi / Later** prompt when the active Kodi session needs to reopen to display saved favourites. A file downloaded by an earlier background sync remains eligible for the prompt until Kodi is actually restarted. Closing uses Kodi’s normal `Quit` command, never a force-stop or profile reload.

## Sync performance (v0.3.16)

- Every sync checks Google Drive journal **metadata**. When Google Drive reports
  an unchanged file ID and version, the local validated cache is reused rather
  than downloading that journal again. Files without a version, an invalid cache,
  or a changed/deleted journal are downloaded or reconciled normally. The cache
  is stored as `favourites-v2-cloud-cache.json` in the add-on data directory and
  is safe to delete; it will be rebuilt on the next sync.
- Device journals and merge snapshots are now written only when their contents
  change. Sync status still records the last check for troubleshooting.
- The **Reduce sync frequency when idle** setting is enabled by default. With
  a five-minute base interval, six consecutive quiet checks increase polling
  to every 15 minutes, and after 24 quiet checks it increases to every 30
  minutes. New detected changes or errors reset the interval to five minutes.
  Disable this setting for a strict five-minute polling interval. **Sync
  favourites now** always runs immediately.
- Journals are *not* compacted: safely deleting old events would require
  evidence that all devices have seen the corresponding deletions.
