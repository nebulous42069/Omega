"""Conservatively replace machine-specific Kodi filesystem paths with special://.

A path is portable only if it sits below a known Kodi root. Other locations,
network URLs, image:// URLs and plugin URLs are deliberately left alone.
This module has no Kodi dependency so its rules can be tested off-device.
"""
import re

from resources.lib.favourites_model import favourite_key

# A complete, quoted filesystem path inside a Kodi builtin command is safe to
# convert; command syntax, plugin URLs and query parameters are NOT rewritten.
_QUOTED = re.compile(r'(?P<quote>[\"\'])(?P<path>.*?)(?P=quote)')
_KODI_SUFFIXES = ("addons/", "userdata/", "media/", "system/", "cache/", "temp/")


def _slash(path):
    return path.replace("\\", "/")


def _is_filesystem_path(value):
    if not isinstance(value, str) or not value or value.lower().startswith("special://"):
        return False
    # No substitutions in SMB shares, URLs, file://, Kodi image:// wrappers or
    # Windows UNC paths. We cannot ensure the same resource exists elsewhere.
    if "://" in value or value.startswith("\\\\") or value.startswith("//"):
        return False
    return bool(value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value))


def _prefix_match(path, prefix):
    path = _slash(path)
    prefix = _slash(prefix).rstrip("/")
    if not prefix:
        return None
    if path.lower() == prefix.lower():
        return ""
    if path.lower().startswith(prefix.lower() + "/"):
        return path[len(prefix) + 1:]
    return None


def _runtime_roots():
    """Get local Kodi roots, most specific first, when its API is available."""
    try:
        from resources.lib.kodi_compat import translate_path, xbmcvfs, xbmc
        if xbmcvfs is None and xbmc is None:
            return []
        roots = []
        for uri in (
            "special://thumbnails/", "special://profile/", "special://masterprofile/",
            "special://xbmcbinaddons/", "special://xbmc/", "special://home/",
        ):
            physical = translate_path(uri)
            if physical and not physical.startswith("special://"):
                roots.append((physical, uri))
        # If profile and masterprofile point to the same directory, prefer
        # masterprofile: it is the stable cross-device name for userdata.
        # A genuinely separate active profile keeps its own profile mapping.
        profile = next((path for path, uri in roots if uri == "special://profile/"), None)
        master = next((path for path, uri in roots if uri == "special://masterprofile/"), None)
        if profile and master and _slash(profile).rstrip("/").lower() == _slash(master).rstrip("/").lower():
            roots = [(path, uri) for path, uri in roots if uri != "special://profile/"]
        roots.sort(key=lambda pair: len(_slash(pair[0])), reverse=True)
        return roots
    except Exception:
        return []


def _portable_home_tail(tail):
    """Use the same canonical URI for userdata on every source platform."""
    if tail.lower().startswith("userdata/thumbnails/"):
        return "special://thumbnails/" + tail[len("userdata/Thumbnails/"):]
    if tail.lower().startswith("userdata/"):
        remainder = tail[len("userdata/"):]
        return "special://masterprofile/" + remainder
    return "special://home/" + tail


def _infer_foreign_kodi_root(value):
    """Recognize Kodi home directories from *other* operating systems.

    Cloud journals may contain old Windows favourites on Android (or vice
    versa). Only recognize unambiguous Kodi roots, never arbitrary 'addons/'
    directories on external disks or network shares.
    """
    path = _slash(value)
    lower = path.lower()
    # Portable installations and Android/Linux dot-kodi user folders.
    for match in re.finditer(r"(?i)/(?:\.kodi|\.xbmc|portable_data)/", path):
        tail = path[match.end():]
        if tail.lower().startswith(_KODI_SUFFIXES):
            return _portable_home_tail(tail)
    # A portable_data directory at the root of a drive also qualifies.
    for match in re.finditer(r"(?i)(?:^|/)(?:portable_data)/", path):
        tail = path[match.end():]
        if tail.lower().startswith(_KODI_SUFFIXES):
            return _portable_home_tail(tail)
    # Windows APPDATA\\Kodi and common Linux .config/kodi installations.
    for match in re.finditer(r"(?i)/(?:AppData/Roaming/Kodi|\.config/kodi)/", path):
        tail = path[match.end():]
        if tail.lower().startswith(_KODI_SUFFIXES):
            return _portable_home_tail(tail)
    # Standard Windows Windows Store/Kodi app paths with a recognizable root.
    # Don't infer from arbitrary 'Kodi' folder names to avoid rewriting media.
    if re.search(r"(?i)/program files(?: \(x86\))?/kodi/", path):
        match = re.search(r"(?i)/program files(?: \(x86\))?/kodi/", path)
        tail = path[match.end():]
        if tail.lower().startswith(("addons/", "media/", "system/")):
            return "special://xbmc/" + tail
    return value


def portable_path(value, roots=None):
    """Convert paths only when they are known to belong to Kodi itself."""
    if not _is_filesystem_path(value):
        return value
    roots = _runtime_roots() if roots is None else roots
    for physical, uri in roots:
        suffix = _prefix_match(value, physical)
        if suffix is not None:
            # Kodi may map special://home and special://profile to nested paths.
            return uri.rstrip("/") + ("/" + suffix if suffix else "/")
    return _infer_foreign_kodi_root(value)


def _normalize_action(action, roots):
    def replace(match):
        old = match.group("path")
        new = portable_path(old, roots)
        return match.group("quote") + new + match.group("quote")
    return _QUOTED.sub(replace, action)


def portable_entry(entry, roots=None):
    """Normalize a favourite's thumbnail and quoted local action paths."""
    roots = _runtime_roots() if roots is None else roots
    new = dict(entry)
    new["thumb"] = portable_path(entry.get("thumb", ""), roots)
    new["action"] = _normalize_action(entry["action"], roots)
    return new


def portable_entries(entries, roots=None):
    """Re-key after action normalization; identical destinations deduplicate."""
    roots = _runtime_roots() if roots is None else roots
    output = {}
    for entry in entries.values():
        new = portable_entry(entry, roots)
        output.setdefault(favourite_key(new), new)
    return output
