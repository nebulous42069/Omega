"""XML and observed-remove-set primitives for household favourites sync.

All operations are deterministic, offline-capable and independent of Kodi imports.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET

MAX_XML_BYTES = 2 * 1024 * 1024
MAX_JOURNAL_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 20000
DEVICE_RE = re.compile(r"^[a-f0-9]{32}$")
EVENT_RE = re.compile(r"^([a-f0-9]{32}):([1-9][0-9]*)$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")


def favourite_key(entry):
    """Identity includes *both* label and Kodi command, avoiding false dedupe."""
    raw = json.dumps([entry["name"], entry["action"]], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_favourites(content):
    if len(content) > MAX_XML_BYTES:
        raise ValueError("favourites.xml exceeds the 2 MB safety limit")
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("DTD/entities are not allowed in favourites.xml")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError("Invalid favourites.xml: %s" % exc)
    if root.tag != "favourites":
        raise ValueError("Expected a <favourites> XML root")
    result = {}
    for child in root:
        if child.tag != "favourite":
            raise ValueError("Unexpected XML element <%s>" % child.tag)
        if list(child):
            raise ValueError("Nested XML inside a favourite is unsupported")
        entry = {
            "name": child.attrib.get("name", ""),
            "thumb": child.attrib.get("thumb", ""),
            "action": child.text or "",
        }
        if not entry["name"] or not entry["action"].strip():
            raise ValueError("Favourite needs both a name and an action")
        result[favourite_key(entry)] = entry
    return result


def write_favourites(entries):
    root = ET.Element("favourites")
    for entry in entries:
        child = ET.SubElement(root, "favourite", {"name": entry["name"], "thumb": entry.get("thumb", "")})
        child.text = entry["action"]
    content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if len(content) > MAX_XML_BYTES:
        raise ValueError("Merged favourites.xml exceeds the 2 MB safety limit")
    return content


def empty_journal(device_id):
    if not DEVICE_RE.fullmatch(device_id):
        raise ValueError("Invalid device identity")
    return {"schema": 2, "device": device_id, "events": []}


def validate_journal(content, expected_device=None):
    if len(content) > MAX_JOURNAL_BYTES:
        raise ValueError("Device sync journal exceeds 8 MB")
    try:
        journal = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid device journal JSON: %s" % exc)
    if not isinstance(journal, dict) or journal.get("schema") != 2:
        raise ValueError("Unsupported device journal format")
    device = journal.get("device", "")
    if not isinstance(device, str) or not DEVICE_RE.fullmatch(device):
        raise ValueError("Malformed device ID in journal")
    if expected_device is not None and device != expected_device:
        raise ValueError("Device ID mismatch in journal")
    events = journal.get("events")
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise ValueError("Too many events in device journal")
    unique = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("Malformed journal event")
        match = EVENT_RE.fullmatch(str(event.get("id", "")))
        if not match or match.group(1) != device or event["id"] in unique:
            raise ValueError("Duplicate or invalid device event ID")
        unique.add(event["id"])
        if not isinstance(event.get("key"), str) or not HASH_RE.fullmatch(event["key"]):
            raise ValueError("Malformed favourite key")
        if event.get("op") == "add":
            entry = event.get("entry")
            if (not isinstance(entry, dict) or
                    not all(isinstance(entry.get(k), str) for k in ("name", "action", "thumb")) or
                    favourite_key(entry) != event["key"]):
                raise ValueError("Invalid add entry in journal")
        elif event.get("op") == "remove":
            seen = event.get("seen")
            if not isinstance(seen, list) or any(not isinstance(x, str) or not EVENT_RE.fullmatch(x) for x in seen):
                raise ValueError("Invalid removal tags")
            if len(seen) > MAX_EVENTS:
                raise ValueError("Too many removal tags")
        else:
            raise ValueError("Unknown sync event operation")
    return journal


def encode_journal(journal):
    content = json.dumps(journal, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")
    validate_journal(content, journal["device"])
    return content


def next_event(journal, op, key, entry=None, seen=None):
    biggest = max([int(e["id"].split(":")[1]) for e in journal["events"]] or [0])
    event = {"id": "%s:%d" % (journal["device"], biggest + 1), "op": op, "key": key}
    if op == "add":
        event["entry"] = entry
    else:
        event["seen"] = sorted(set(seen or []))
    journal["events"].append(event)
    return event


def merge_journal_versions(local, remote):
    if local["device"] != remote["device"]:
        raise ValueError("Cannot merge different device journals")
    by_id = {event["id"]: event for event in remote["events"]}
    for event in local["events"]:
        previous = by_id.get(event["id"])
        if previous is not None and previous != event:
            raise ValueError("Conflicting events for same device ID (cloned profile?)")
        by_id[event["id"]] = event
    events = sorted(by_id.values(), key=lambda e: int(e["id"].split(":")[1]))
    return {"schema": 2, "device": local["device"], "events": events}


def materialize(journals):
    """Observed-remove set: deletion removes only add tags seen by that device.

    Concurrent unobserved adds survive, preventing last-writer-wins data loss.
    """
    additions = {}
    removed = set()
    for journal in journals:
        for event in journal["events"]:
            if event["op"] == "add":
                additions[event["id"]] = event
            else:
                removed.update(event["seen"])
    tags = {}
    entry_by_key = {}
    for event_id, event in sorted(additions.items()):
        if event_id not in removed:
            key = event["key"]
            tags.setdefault(key, []).append(event_id)
            # Stable choice when the same label and command have different thumbnails.
            entry_by_key.setdefault(key, event["entry"])
    return entry_by_key, tags


def changed_by_user(local, baseline_entries, baseline_tags, current_entries, current_tags,
                    journal, initial=False, protected=None, blocked_additions=None):
    """Derive local edits *only* relative to the device's last applied snapshot."""
    protected = set(protected or [])
    blocked_additions = set(blocked_additions or [])
    added = removed = skipped = 0
    if initial:
        for key, entry in local.items():
            # A joining device merges missing items, but does not produce a
            # redundant add tag for entries already in the shared set. This
            # lets another paired device later delete that entry reliably.
            if key not in current_entries:
                next_event(journal, "add", key, entry=entry)
                added += 1
        return added, removed, skipped

    for key, entry in local.items():
        if key not in baseline_entries:
            if key in blocked_additions:
                # Kodi's stale in-memory view may have reintroduced a favourite
                # which another device removed. Wait for a clean restart.
                skipped += 1
                continue
            # This add was made locally since the last sync, even if another
            # device concurrently added an identical favourite.
            next_event(journal, "add", key, entry=entry)
            added += 1
        elif entry != baseline_entries[key] and key not in protected:
            # Thumbnail change: tombstone the previously seen tags and add
            # the updated entry. Concurrent unobserved adds are not deleted.
            seen = baseline_tags.get(key, [])
            if seen:
                next_event(journal, "remove", key, seen=seen)
            next_event(journal, "add", key, entry=entry)
            added += 1
    for key in baseline_entries:
        if key not in local:
            if key in protected:
                skipped += 1
                continue
            seen = baseline_tags.get(key, [])
            if seen:
                next_event(journal, "remove", key, seen=seen)
                removed += 1
    return added, removed, skipped
