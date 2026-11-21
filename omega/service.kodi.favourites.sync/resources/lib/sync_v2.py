"""Bidirectional favourites sync using one append-only Google Drive journal per device.

The old single shared favourites.xml is imported once (if no v2 logs exist)
then left untouched. Devices never patch another device's journal.
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import uuid

from resources.lib.drive_api import DriveError
from resources.lib.favourites_model import (
    DEVICE_RE, changed_by_user, empty_journal, encode_journal, favourite_key,
    materialize, merge_journal_versions, read_favourites, validate_journal,
    write_favourites, next_event,
)
from resources.lib.kodi_compat import get_setting_string, log, now_iso
from resources.lib.portable_paths import portable_entry, portable_entries, _runtime_roots

JOURNAL_PREFIX = "kodi-favourites-v2-"
JOURNAL_RE = re.compile(r"^kodi-favourites-v2-([a-f0-9]{32})\.json$")
LOCAL_SNAPSHOT = "favourites-v2-state.json"
LOCAL_JOURNAL = "favourites-v2-journal.json"
LOCAL_DEVICE = "favourites-v2-device.json"
REMOTE_CACHE = "favourites-v2-cloud-cache.json"
# A corrupt, stale, or unversioned cache never suppresses a cloud download.
MAX_CACHE_BYTES = 96 * 1024 * 1024
LOCK_DIR = ".favourites-sync-lock"
BACKUP_DIR = "favourites-sync-backups"


def _atomic_write(path, content):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".sync-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _atomic_json(path, value):
    _atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))


def _load_json(path, default=None):
    if not os.path.isfile(path):
        return default
    with open(path, "rb") as handle:
        return json.load(handle)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _read_file(path):
    with open(path, "rb") as handle:
        return handle.read()


def _get_device_id(profile):
    path = os.path.join(profile, LOCAL_DEVICE)
    record = _load_json(path)
    if record is None:
        device = uuid.uuid4().hex
        _atomic_json(path, {"device": device})
        return device
    if not isinstance(record, dict) or not DEVICE_RE.fullmatch(str(record.get("device", ""))):
        raise ValueError("Invalid local device ID; restore it from backup")
    return record["device"]


def _load_snapshot(profile):
    saved = _load_json(os.path.join(profile, LOCAL_SNAPSHOT))
    if saved is None:
        return None
    if not isinstance(saved, dict) or saved.get("schema") != 2:
        raise ValueError("Unknown local sync snapshot; refusing unsafe migration")
    if not isinstance(saved.get("entries"), dict) or not isinstance(saved.get("tags"), dict):
        raise ValueError("Corrupted local sync snapshot")
    return saved


def _load_local_journal(profile, device_id):
    path = os.path.join(profile, LOCAL_JOURNAL)
    if not os.path.isfile(path):
        return empty_journal(device_id)
    return validate_journal(_read_file(path), device_id)


def _write_if_changed(path, content):
    """Avoid a flash write and fsync when the bytes are already identical."""
    if os.path.isfile(path) and _read_file(path) == content:
        return False
    _atomic_write(path, content)
    return True


def _save_journal(profile, journal):
    return _write_if_changed(os.path.join(profile, LOCAL_JOURNAL), encode_journal(journal))


def _backup_before_replace(profile, original_path):
    if not os.path.isfile(original_path):
        return None
    backup_dir = os.path.join(profile, BACKUP_DIR)
    os.makedirs(backup_dir, exist_ok=True)
    filename = "favourites-%s-%s.xml" % (time.strftime("%Y%m%d-%H%M%S"), uuid.uuid4().hex[:6])
    destination = os.path.join(backup_dir, filename)
    shutil.copy2(original_path, destination)
    backups = sorted((os.path.join(backup_dir, x) for x in os.listdir(backup_dir)
                      if x.startswith("favourites-") and x.endswith(".xml")))
    for old in backups[:-10]:
        os.unlink(old)
    return destination


class SyncLock:
    def __init__(self, profile):
        self.lock = os.path.join(profile, LOCK_DIR)
        self.acquired = False

    def __enter__(self):
        try:
            os.mkdir(self.lock)
        except FileExistsError:
            # Lock can remain after Kodi crashes. Only remove after 3 minutes.
            if time.time() - os.stat(self.lock).st_mtime < 180:
                raise DriveError("Another sync is already running")
            os.rmdir(self.lock)
            os.mkdir(self.lock)
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.acquired:
            try:
                os.rmdir(self.lock)
            except OSError:
                pass


def _load_remote_cache(profile):
    """Return the *validated-by-usage* cache envelope, never a source of truth."""
    path = os.path.join(profile, REMOTE_CACHE)
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > MAX_CACHE_BYTES:
            return {}
        cache = _load_json(path, {})
        if isinstance(cache, dict) and cache.get("schema") == 1 and isinstance(cache.get("files"), dict):
            return cache["files"]
    except (ValueError, OSError, UnicodeError):
        pass
    return {}


def _cache_record(meta, journal):
    # Drive's monotonically increasing version is necessary to trust cache.
    # A modified timestamp or file size alone cannot prove that bytes match.
    version = str(meta.get("version") or "")
    if not version or not meta.get("id"):
        return None
    return {
        "id": meta["id"],
        "version": version,
        "size": meta.get("size"),
        "sha256": _sha(encode_journal(journal)),
        "journal": journal,
    }


def _save_remote_cache(profile, files):
    envelope = {"schema": 1, "files": files}
    path = os.path.join(profile, REMOTE_CACHE)
    payload = json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    _write_if_changed(path, payload)


def _fetch_journals(client, profile=None):
    """List cloud metadata, downloading only unknown/changed journal versions.

    Never trust only an mtime or size. A missing version, corrupt cache, changed
    ID or a deleted device log forces revalidation. Duplicates remain fatal.
    """
    previous = _load_remote_cache(profile) if profile else {}
    metas = client.list_appdata_files(JOURNAL_PREFIX)
    seen_names = set()
    journals = {}
    remote_by_device = {}
    next_cache = {}
    remote_changed = False
    for meta in metas:
        name = meta.get("name", "")
        match = JOURNAL_RE.fullmatch(name)
        if not match:
            continue
        if name in seen_names:
            raise DriveError("Duplicate device journals in Google Drive: %s" % name)
        seen_names.add(name)
        device = match.group(1)
        if meta.get("size") and meta["size"] > 8 * 1024 * 1024:
            raise DriveError("Oversize Google Drive journal: %s" % name)
        old = previous.get(device)
        version = str(meta.get("version") or "")
        unchanged = (version and isinstance(old, dict)
                     and old.get("id") == meta["id"]
                     and old.get("version") == version
                     and old.get("size") == meta.get("size"))
        journal = None
        if unchanged:
            try:
                # Validate even cached content. Corrupt caches must not hide
                # remote changes or silently erase favourites.
                raw = json.dumps(old["journal"], ensure_ascii=False).encode("utf-8")
                journal = validate_journal(raw, device)
                if _sha(encode_journal(journal)) != old.get("sha256"):
                    raise ValueError("Cached journal checksum mismatch")
            except (TypeError, KeyError, ValueError, UnicodeError):
                journal = None
        if journal is None:
            journal = validate_journal(client.download_file(meta["id"]), device)
            remote_changed = True
        record = _cache_record(meta, journal)
        if record is not None:
            next_cache[device] = record
        journals[device] = journal
        remote_by_device[device] = meta
    if set(previous) != set(next_cache):
        remote_changed = True
    return journals, remote_by_device, next_cache, remote_changed


def _prior_legacy_favourites(client, addon):
    """Import the old cloud XML only on the creation of the first v2 log."""
    filename = get_setting_string(addon, "remote_filename", "favourites.xml")
    result = {}
    # The original uploader could create duplicate files with the same name.
    # Import all of them once, instead of losing a valid legacy collection.
    for meta in client.list_appdata_files(filename):
        if meta["name"] != filename:
            continue
        result.update(read_favourites(client.download_file(meta["id"])))
    return result


def _visible_order(local, global_entries):
    # Keep each user's familiar local ordering; append new remote entries.
    keys = [key for key in local if key in global_entries]
    keys.extend(key for key in sorted(global_entries) if key not in local)
    return [global_entries[key] for key in keys]


def _same_entries(local, target):
    # xml formatting and ordering do not count as edits (do not churn Kodi file).
    return local == target



def _upgrade_cloud_paths(journal, remote_journals, roots):
    """Replace observed absolute Kodi paths using ordinary v2 add/remove events.

    Cloud journals are append-only and owned by other devices; never rewrite
    those histories. The local device can instead record replacement events.
    Both existing and future devices can then consume the canonical entries.
    """
    entries, tags = materialize(remote_journals.values())
    migrated = 0
    staged = set()
    for key, entry in entries.items():
        new = portable_entry(entry, roots)
        if new == entry:
            continue
        canonical_key = favourite_key(new)
        seen = tags.get(key, [])
        if not seen:
            continue
        next_event(journal, "remove", key, seen=seen)
        if canonical_key == key or (canonical_key not in entries and canonical_key not in staged):
            next_event(journal, "add", canonical_key, entry=new)
            staged.add(canonical_key)
        migrated += 1
    return migrated


def _portable_snapshot(snapshot, roots, current_tags):
    """Translate old snapshots so upgrading does not invent user edits.

    If a key changes because an absolute path in its ACTION becomes special://,
    adopt the tags of the newly canonicalized cloud entry for future removals.
    This preserves the existing observed-remove semantics after migration.
    """
    if not snapshot:
        return {}, {}, set(), set()
    entries = {}
    tags = {}
    mapped = {}
    for old_key, entry in snapshot.get("entries", {}).items():
        new = portable_entry(entry, roots)
        key = favourite_key(new)
        mapped[old_key] = key
        entries[key] = new
        if key != old_key or new != entry:
            tags[key] = list(current_tags.get(key, []))
        else:
            tags[key] = list(snapshot.get("tags", {}).get(old_key, []))
    protected = {mapped.get(key, key) for key in snapshot.get("protected", [])}
    blocked = {mapped.get(key, key) for key in snapshot.get("blocked_additions", [])}
    return entries, tags, protected, blocked


def perform_household_sync(client, addon, addon_profile, local_path, reason="manual"):
    """Run one full sync; caller handles errors and status persistence.

    Local journal is always persisted before a cloud upload. Snapshot is saved
    only after the resulting local XML is applied successfully.
    """
    with SyncLock(addon_profile):
        device = _get_device_id(addon_profile)
        snapshot = _load_snapshot(addon_profile)
        journal = _load_local_journal(addon_profile, device)
        local_journal_exists = os.path.isfile(os.path.join(addon_profile, LOCAL_JOURNAL))
        initial = snapshot is None
        local_missing = not os.path.isfile(local_path)
        local_bytes = b"" if local_missing else _read_file(local_path)
        local_raw = {} if local_missing else read_favourites(local_bytes)
        roots = _runtime_roots()
        local = portable_entries(local_raw, roots)
        local_sha = _sha(local_bytes)

        remote_journals, remote_by_device, cache_files, cloud_changed = _fetch_journals(client, addon_profile)
        if not remote_by_device or (device not in remote_by_device and not local_journal_exists):
            # New Google account, wiped appdata, or a lost own journal:
            # never interpret an empty server as a mass deletion.
            initial = True
        remote_own = remote_journals.get(device, empty_journal(device))
        journal = merge_journal_versions(journal, remote_own)
        remote_journals[device] = journal
        cloud_entries, cloud_tags = materialize(remote_journals.values())

        # In-place upgrade path for users of v0.2.36: seed v2 from the last
        # legacy cloud copy, but never overwrite or delete the old XML.
        migrated = 0
        if initial and not remote_by_device:
            legacy_entries = portable_entries(_prior_legacy_favourites(client, addon), roots)
            for key, entry in legacy_entries.items():
                if key not in cloud_entries:
                    next_event(journal, "add", key, entry=entry)
                    cloud_entries[key] = entry
                    migrated += 1
            remote_journals[device] = journal
            cloud_entries, cloud_tags = materialize(remote_journals.values())

        # Migrate old cloud entries as observed, without editing other devices'
        # journals. This also fixes old Windows thumbnails when a new Android
        # device joins the same shared collection.
        path_upgrades = _upgrade_cloud_paths(journal, remote_journals, roots)
        cloud_entries, cloud_tags = materialize(remote_journals.values())
        base_entries, base_tags, old_protected, old_blocked = _portable_snapshot(
            snapshot, roots, cloud_tags)
        if snapshot and reason == "startup" and snapshot.get("written_sha") == local_sha:
            # A restart happened with the previously merged file intact.
            # From now on intentional user edits of those entries count.
            old_protected.clear()
            old_blocked.clear()
        if local_missing and not initial:
            # A missing XML must NEVER be interpreted as 'delete everything'.
            # Recreate from the shared collection instead.
            local_changes = (0, 0, 0)
        else:
            local_changes = changed_by_user(
                local, base_entries, base_tags, cloud_entries, cloud_tags,
                journal, initial=initial, protected=old_protected,
                blocked_additions=old_blocked)

        # Journals from remote and the current device may have been merged;
        # validate and save pending events locally before any network write.
        _save_journal(addon_profile, journal)
        serialized = encode_journal(journal)
        uploaded_journal = False
        if serialized != encode_journal(remote_own) or device not in remote_by_device:
            filename = "%s%s.json" % (JOURNAL_PREFIX, device)
            meta = remote_by_device.get(device)
            if meta:
                uploaded_meta = client.update_file(meta["id"], filename, serialized)
            else:
                uploaded_meta = client.create_file("", filename, serialized, remote_mode="appdata")
            uploaded_journal = True
            # Cache only the revision acknowledged by Google Drive. If the
            # response omits its version, the next sync downloads it safely.
            record = _cache_record(uploaded_meta or {}, journal) if uploaded_meta else None
            if record is not None:
                cache_files[device] = record
            else:
                cache_files.pop(device, None)

        global_entries, global_tags = materialize(remote_journals.values())
        pending_protected = {key for key in old_protected if key in global_entries}
        added_by_cloud = set(global_entries) - set(local)
        pending_protected.update(added_by_cloud)
        # Similarly protect remote DELETIONS: Kodi may write a cached older
        # in-memory favourites list after this service removes one on disk.
        pending_blocked = {key for key in old_blocked if key not in global_entries}
        pending_blocked.update(set(local) - set(global_entries))

        wrote_local = False
        if not _same_entries(local, global_entries) or local_raw != local:
            # Do not clobber a favourites edit that happened during networking.
            current_bytes = b"" if not os.path.isfile(local_path) else _read_file(local_path)
            if _sha(current_bytes) != local_sha:
                raise DriveError("Kodi favourites changed during sync; retrying on next cycle")
            output = write_favourites(_visible_order(local, global_entries))
            _backup_before_replace(addon_profile, local_path)
            _atomic_write(local_path, output)
            wrote_local = True
            local_sha = _sha(output)
        # Only write the snapshot when its actual merge state changes.
        # last_success is diagnostic metadata, not a reason for a disk write.
        snapshot_core = {
            "schema": 2,
            "entries": global_entries,
            "tags": global_tags,
            "protected": sorted(pending_protected),
            "blocked_additions": sorted(pending_blocked),
            "written_sha": local_sha,
        }
        if snapshot is None or any(snapshot.get(k) != v for k, v in snapshot_core.items()):
            snapshot_core["last_success"] = now_iso()
            _atomic_json(os.path.join(addon_profile, LOCAL_SNAPSHOT), snapshot_core)
        # The cache is a performance hint: write only *after* the XML and
        # snapshot have been applied successfully, never following a failure.
        _save_remote_cache(addon_profile, cache_files)

        return {
            "status": "ok",
            "direction": "merge" if (wrote_local or any(local_changes[:2]) or migrated or path_upgrades) else "noop",
            "message": ("Merged %d favourites (%d local additions, %d deletions, %d legacy imports)%s%s" % (
                len(global_entries), local_changes[0], local_changes[1], migrated,
                "; updated XML may appear in Kodi after its next normal launch" if wrote_local else "",
                "; some changes deferred until Kodi restarts" if local_changes[2] else "")),
            "completed_at": now_iso(),
            "count": len(global_entries),
            "changed_local_file": wrote_local,
            "cloud_changed": cloud_changed,
            "uploaded_journal": uploaded_journal,
            # Only a first-time import of previously unseen cloud favourites
            # should offer a Kodi restart. Routine two-way merges never do.
            "first_cloud_import": bool(initial and wrote_local and added_by_cloud),
            "imported_count": len(added_by_cloud),
            "protected_count": len(pending_protected),
            "normalized_paths": path_upgrades + sum(1 for entry in local_raw.values()
                                                 if portable_entry(entry, roots) != entry),
        }
