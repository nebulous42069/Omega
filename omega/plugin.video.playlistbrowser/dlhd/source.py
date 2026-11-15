"""Resolve the configured DaddyLive site consistently across Kodi entry points."""
from urllib.parse import urlsplit

DEFAULT_BASE = 'https://thedaddy.li'
LEGACY_BASE = 'https://dlive.sx'


def source_base(addon):
    base = (addon.getSetting('DLHD_base') or '').strip().rstrip('/')
    if not base or base.lower() == LEGACY_BASE:
        return DEFAULT_BASE
    return base


def source_host(base):
    return urlsplit(base).hostname or 'unknown'
