"""Safe JSON cache of parsed XMLTV records, shared across Kodi invocations."""
import hashlib
import json
import os
from datetime import datetime
from epg_cache import atomic_write

VERSION = 1


def fingerprint(xml_bytes):
    return hashlib.sha256(xml_bytes).hexdigest()


def cache_path(xml_path):
    return xml_path + '.processed.json'


def load(xml_path, digest):
    try:
        with open(cache_path(xml_path), encoding='utf-8') as stream:
            data = json.load(stream)
        if data['version'] != VERSION or data['digest'] != digest:
            return None
        channels = data['channels']
        if not isinstance(channels, dict) or any(not isinstance(v, dict) for v in channels.values()):
            return None
        programmes = {}
        for cid, records in data['programmes'].items():
            rows = []
            for record in records:
                start, stop = datetime.fromisoformat(record[0]), datetime.fromisoformat(record[1])
                if start.tzinfo is None or stop.tzinfo is None:
                    return None
                rows.append({'start': start, 'stop': stop, 'title': record[2], 'desc': record[3]})
            programmes[cid] = rows
        return channels, programmes
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError):
        return None


def save(xml_path, digest, channels, programmes):
    data = {'version': VERSION, 'digest': digest, 'channels': channels,
            'programmes': {cid: [[p['start'].isoformat(), p['stop'].isoformat(), p['title'], p['desc']]
                                for p in rows] for cid, rows in programmes.items()}}
    # Atomic replacement lets separate plugin/service interpreters read safely.
    atomic_write(cache_path(xml_path), json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
