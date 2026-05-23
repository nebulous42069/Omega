"""Shared utilities for debrid service modules.

Provides:
- Cached IP lookup for CDN passthrough
- Smart auto-delete runtime helpers
"""

import json
import time

from resources.lib.modules.globals import g

# ─── IP Passthrough (cached) ────────────────────────────────────────────────

_cached_ip = None
_cached_ip_time = 0
_IP_CACHE_TTL = 300  # 5 minutes


def get_user_ip():
    """Fetch the user's public IP, cached for 5 minutes.
    Used by debrid services that support IP passthrough for CDN routing."""
    global _cached_ip, _cached_ip_time

    now = time.time()
    if _cached_ip and (now - _cached_ip_time) < _IP_CACHE_TTL:
        return _cached_ip

    try:
        import requests
        resp = requests.get("https://api.ipify.org", timeout=3)
        if resp.ok and resp.text:
            _cached_ip = resp.text.strip()
            _cached_ip_time = now
            return _cached_ip
    except Exception:
        pass

    return _cached_ip  # Return stale cache on failure, or None


# ─── Smart Auto-Delete Helpers ──────────────────────────────────────────────

_PENDING_KEY = "debrid.pending_cleanup"


def store_pending_cleanup(service, item_id, delete_method_name="delete_torrent"):
    """Store a debrid item for potential post-playback cleanup.

    Args:
        service: debrid service name ('real_debrid', 'premiumize', 'all_debrid', 'torbox')
        item_id: the torrent/transfer/magnet ID to track
        delete_method_name: name of the delete method on the debrid class
    """
    data = json.dumps({
        "service": service,
        "item_id": str(item_id),
        "delete_method": delete_method_name,
    })
    g.set_runtime_setting(_PENDING_KEY, data)
    g.log(f"Smart delete: stored pending cleanup for {service} id={item_id}", "info")


def get_pending_cleanup():
    """Retrieve and clear the pending cleanup info.

    Returns dict with {service, item_id, delete_method} or None."""
    raw = g.get_runtime_setting(_PENDING_KEY)
    if not raw:
        return None
    # Clear immediately so it doesn't fire twice
    g.set_runtime_setting(_PENDING_KEY, "")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
