"""
Resolver Module for resolving supplied source information into an object that can be played through Player module
"""
import importlib
import re
import sys
from urllib import parse

import requests
import xbmcgui
import xbmcvfs

from resources.lib.common.thread_pool import ThreadPool
from resources.lib.debrid.all_debrid import AllDebrid
from resources.lib.debrid.debrid_link import DebridLink
from resources.lib.debrid.premiumize import Premiumize
from resources.lib.debrid.real_debrid import RealDebrid
from resources.lib.debrid.torbox import TorBox
from resources.lib.modules.exceptions import CloudMiss
from resources.lib.modules.exceptions import FileIdentification
from resources.lib.modules.exceptions import InfringingFile
from resources.lib.modules.exceptions import ResolverFailure
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.globals import g
from resources.lib.modules.resolver.torrent_resolvers import AllDebridResolver
from resources.lib.modules.resolver.torrent_resolvers import DebridLinkResolver
from resources.lib.modules.resolver.torrent_resolvers import PremiumizeResolver
from resources.lib.modules.resolver.torrent_resolvers import RealDebridResolver
from resources.lib.modules.resolver.content_verifier import ContentVerifier
from resources.lib.modules.resolver.torrent_resolvers import TorBoxResolver

# Maps debrid_provider source field to DebridCache DB service key.
# Used both in the CloudMiss handler and the file-not-found handler.
_DEBRID_PROVIDER_TO_DB_KEY = {
    'real_debrid': 'rd', 'all_debrid': 'ad', 'premiumize': 'pm',
    'torbox': 'tb', 'debrid_link': 'dl',
}


# Batch D / S13 — Feature #3 last-resolved quality memory.
# Maps the internal debrid_provider key to a human-readable label that
# OpenInfo's skin can render directly. Unknown providers fall back to a
# title-cased version of the raw key.
_DEBRID_DISPLAY_LABEL = {
    'real_debrid': 'Real-Debrid',
    'all_debrid': 'AllDebrid',
    'premiumize': 'Premiumize',
    'torbox': 'TorBox',
    'debrid_link': 'Debrid-Link',
}

# Cap on how many entries we keep in the resolutions cache. The dict is
# keyed by show/movie imdb_id, so this bounds the file at roughly 200
# rows × ~250 bytes ≈ 50 KB. Eviction is oldest-first by `timestamp`.
_LAST_RESOLUTIONS_MAX_ENTRIES = 200

# Filename used for the resolutions cache. Lives in Seren's own
# addon_data so OpenInfo reads it cross-addon (one-way dependency:
# OpenInfo knows about Seren, not the other way around).
_LAST_RESOLUTIONS_FILE = 'openinfo_last_resolutions.json'


def _stash_last_resolution(source, item_information, release_title):
    """Write/update the last-resolution record for this title.

    Keyed by `imdb_id` of the parent show (for episodes) or the movie
    itself, so the OpenInfo dialog can look it up via the same id it
    already has on `info_dict['imdb_id']`. The cache is plain JSON,
    written atomically (tmp + replace), capped at
    _LAST_RESOLUTIONS_MAX_ENTRIES rows.

    Silently no-ops on any failure — playback has already succeeded by
    the time this runs and a cache write must never affect that."""
    import json
    import os
    import tempfile
    import time
    import xbmcvfs

    info = item_information.get('info', {}) or {}
    mediatype = info.get('mediatype', '')
    # For episodes use the SHOW's imdb_id (info has it under
    # 'tvshow.imdb_id') so the dialog and the show dialog can both
    # surface the most recent episode resolution.
    if mediatype == 'episode':
        imdb_id = info.get('tvshow.imdb_id') or info.get('imdb_id') or ''
    else:
        imdb_id = info.get('imdb_id') or ''

    imdb_id = str(imdb_id or '').strip()
    if not imdb_id:
        # Nothing to key on — silently skip rather than fall back to
        # tmdb/trakt and risk a key collision when a future read uses
        # imdb_id only.
        return

    cache_dir = xbmcvfs.translatePath(g.ADDON_USERDATA_PATH)
    cache_path = os.path.join(cache_dir, _LAST_RESOLUTIONS_FILE)

    # Build the new entry. Keep it compact — these properties go
    # straight to a Kodi window property; bigger payloads waste skin
    # parse time.
    debrid_key = str(source.get('debrid_provider') or '').strip()
    quality = str(source.get('quality') or '').strip()
    title = (info.get('title') or info.get('tvshowtitle') or '')[:200]

    entry = {
        'imdb_id': imdb_id,
        'mediatype': mediatype or 'movie',
        'title': title,
        'quality': quality,
        'debrid': debrid_key,
        'debrid_label': _DEBRID_DISPLAY_LABEL.get(debrid_key, debrid_key.replace('_', '-').title()),
        'release_title': str(release_title or source.get('release_title') or '')[:300],
        'timestamp': int(time.time()),
    }
    if mediatype == 'episode':
        try:
            entry['season'] = int(info.get('season') or 0)
            entry['episode'] = int(info.get('episode') or 0)
        except (TypeError, ValueError):
            pass

    # Read existing cache (best effort)
    cache = {}
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as fh:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    cache = loaded
    except (OSError, IOError, ValueError):
        cache = {}

    cache[imdb_id] = entry

    # Bound the cache. JSON dicts in Py3.7+ preserve insertion order;
    # we sort by timestamp asc and keep the most-recent N. Doing this on
    # every write is fine — N is small and the read side doesn't care
    # about order.
    if len(cache) > _LAST_RESOLUTIONS_MAX_ENTRIES:
        try:
            ranked = sorted(
                cache.items(),
                key=lambda kv: int(kv[1].get('timestamp', 0)) if isinstance(kv[1], dict) else 0,
                reverse=True,
            )
            cache = dict(ranked[:_LAST_RESOLUTIONS_MAX_ENTRIES])
        except Exception:
            # If anything in the cache is malformed, drop everything
            # except the entry we're writing — better than blocking the
            # write on a corrupted record.
            cache = {imdb_id: entry}

    # Atomic write: dump to a tmp file in the same directory, then
    # os.replace() — survives a Kodi force-quit mid-write without
    # leaving a half-truncated JSON behind.
    try:
        os.makedirs(cache_dir, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix='.openinfo_last_resolutions.', suffix='.tmp', dir=cache_dir)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fh:
                json.dump(cache, fh, ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp_path, cache_path)
        except Exception:
            # Best effort cleanup if the rename failed
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except (OSError, IOError, ValueError):
        # Disk full / permission denied / serialization error — log and
        # drop. Never raise; the caller is the play path.
        g.log(f"Failed to write last-resolutions cache for {imdb_id}", "debug")


class Resolver:
    """
    Handles resolving of identified sources to a playable format to supply to Player module
    """

    torrent_resolve_failure_style = None

    def __init__(self):
        self.torrent_resolve_failure_style = g.get_int_setting('general.resolvefailurehandling')
        sys.path.append(g.ADDON_USERDATA_PATH)
        self.return_data = None
        self.resolvers = {
            "all_debrid": AllDebridResolver,
            "debrid_link": DebridLinkResolver,
            "premiumize": PremiumizeResolver,
            "real_debrid": RealDebridResolver,
            "torbox": TorBoxResolver,
        }

    def resolve_multiple_until_valid_link(self, sources, item_information, pack_select=False, silent=False):
        """
        Resolves all supplied sources until an identified link is found.
        Includes content verification — if the resolved source's release title
        doesn't match the expected movie/episode, it's skipped and the next
        source is tried. After N consecutive mismatches (default 3), a rescrape
        is signaled via runtime setting.

        Cloud miss detection: if a torrent source was expected to be cached
        but the debrid service reports it's no longer available, it's counted
        as a cloud miss. After N consecutive cloud misses (default 3), a
        rescrape is triggered to find fresh cached sources.

        :param sources: List of sources to resolve
        :param item_information: Metadata on item intended to be played
        :param pack_select: Set to True to force manual file selection
        :return: streamable URL or dictionary of adaptive source information
        """
        stream_link = None
        release_title = None
        verifier = ContentVerifier(item_information, sources)
        cloud_miss_count = 0
        cloud_miss_threshold = g.get_int_setting("general.cloudMissThreshold", 3)

        for source in sources:
            try:
                stream_link, release_title = self.resolve_single_source(source, item_information, pack_select, silent)

                if stream_link is None and source.get('_cloud_miss'):
                    # Don't count cloud misses for fallback-cached sources —
                    # they were never confirmed cached, so misses are expected.
                    if source.get('_cache_fallback'):
                        g.log(
                            f"Cloud miss (fallback source, not counted): "
                            f"{source.get('debrid_provider', '?')} — "
                            f"{source.get('release_title', 'N/A')}",
                            "debug",
                        )
                        continue
                    cloud_miss_count += 1
                    g.log(
                        f"Cloud miss {cloud_miss_count}/{cloud_miss_threshold}: "
                        f"{source.get('debrid_provider', '?')} no longer has "
                        f"{source.get('release_title', 'N/A')}",
                        "warning",
                    )
                    if cloud_miss_count >= cloud_miss_threshold:
                        g.log(
                            f"Cloud miss threshold reached ({cloud_miss_count}) — "
                            f"signaling rescrape",
                            "warning",
                        )
                        g.set_runtime_setting("cloud_miss_rescrape", "true")
                        break
                    continue

                if stream_link:
                    # Content verification: does the resolved source match expected content?
                    if not verifier.verify(source, release_title):
                        g.log(
                            f"Content verification: Skipping mismatched source — "
                            f"'{release_title or source.get('release_title', 'N/A')}'",
                            "warning",
                        )
                        stream_link = None
                        release_title = None

                        # Check if mismatch threshold reached → signal rescrape
                        if verifier.should_rescrape():
                            g.set_runtime_setting("content_verify_rescrape", "true")
                            break
                        continue
                    # Save winning title for reorder_sources() on next play.
                    if release_title:
                        g.set_setting('resolver.last_played_source', release_title)
                    # Batch D / S13 — Feature #3: stash a tiny "last played" record
                    # for OpenInfo's dialog. Done here (right before `break`) so it
                    # only fires on a verified, going-to-be-played source — not on
                    # ones that resolved but failed content verification above.
                    # Wrapped in its own try so any cache failure can never block
                    # playback that has already succeeded.
                    try:
                        _stash_last_resolution(source, item_information, release_title)
                    except Exception:
                        g.log_stacktrace()
                    break
            except Exception:
                g.log_stacktrace()
                continue

        return stream_link, release_title

    def resolve_single_source(self, source, item_information, pack_select=False, silent=False):
        """
        Resolves source to a streamable object
        :param source: Item to attempt to resolve
        :param item_information: Metadata on item intended to be played
        :param pack_select: Set to True to force manual file selection
        :return: streamable URL or dictionary of adaptive source information
        """

        stream_link = None

        try:
            if source["type"] == "adaptive":
                stream_link = source
            elif source["type"] == "direct":
                stream_link = source["url"]
            elif source["type"] == "torrent":
                stream_link = self._resolve_debrid_source(
                    self.resolvers[source["debrid_provider"]],
                    source,
                    item_information,
                    pack_select,
                )

                if (
                    not stream_link
                    and self.torrent_resolve_failure_style == 1
                    and not pack_select
                    and not silent
                    and xbmcgui.Dialog().yesno(g.ADDON_NAME, g.get_language_string(30490))
                ):
                    stream_link = self._resolve_debrid_source(
                        self.resolvers[source["debrid_provider"]],
                        source,
                        item_information,
                        True,
                    )

            elif source["type"] in ["hoster", "cloud"]:
                stream_link = self._resolve_hoster_or_cloud(source, item_information)

            if stream_link:
                return stream_link, source['release_title']
            g.log(f"Failed to resolve source: {source}", "error")
            return None, None
        except ResolverFailure as e:
            g.log(f'Failed to resolve source: {e}')
            return None, None

    @staticmethod
    def _handle_provider_imports_resolving(source):
        provider = source["provider_imports"]
        provider_module = importlib.import_module(f"{provider[0]}.{provider[1]}")
        if hasattr(provider_module, "source"):
            provider_module = provider_module.source()

        source["url"] = provider_module.resolve(source["url"])
        return source

    def _handle_debrid_hoster_resolving(self, source, item_information):
        stream_link = self._resolve_debrid_source(
            self.resolvers[source["debrid_provider"]], source, item_information, False
        )

        if not stream_link:
            return
        try:
            requests.head(stream_link, timeout=3)
            return stream_link
        except requests.exceptions.RequestException as e:
            g.log(e, 'error')
            g.log("Head Request failed link likely dead, skipping", 'error')
            return

    def _resolve_hoster_or_cloud(self, source, item_information):
        stream_link = None

        if not source.get("url", False):
            return

        if source["type"] == "cloud" and source["debrid_provider"] == "premiumize":
            selected_file = Premiumize().item_details(source["url"])
            if not selected_file or selected_file.get("status") == "error":
                return None
            key = "stream_link" if g.get_bool_setting("premiumize.transcoded") else "link"
            return selected_file.get(key)

        if "provider_imports" in source:
            source = self._handle_provider_imports_resolving(source)

        if "debrid_provider" in source:
            stream_link = self._handle_debrid_hoster_resolving(source, item_information)
        elif source["url"].startswith("http"):
            stream_link = self._test_direct_url(source)
        elif xbmcvfs.exists(source["url"]):
            stream_link = source["url"]

        if stream_link is None:
            return
        if stream_link.endswith(".rar"):
            return

        return stream_link

    @staticmethod
    def _test_direct_url(source):
        try:
            ext = source["url"].split("?")[0]
            ext = ext.split("&")[0]
            ext = ext.split("|")[0]
            ext = ext.rsplit(".")[-1]
            ext = ext.replace("/", "").lower()
            if ext == "rar":
                raise TypeError("Incorrect file format - rar file provided")

            try:
                headers = source["url"].rsplit("|", 1)[1]
            except IndexError:
                headers = ""

            headers = parse.quote_plus(headers).replace("%3D", "=") if " " in headers else headers
            headers = dict(parse.parse_qsl(headers))

            live_check = requests.head(source["url"], headers=headers, timeout=10)

            if live_check.status_code != 200:
                g.log("Head Request failed link likely dead, skipping")
                return

            stream_link = source["url"]
        except (IndexError, KeyError):
            stream_link = None
        return stream_link

    @staticmethod
    def _resolve_debrid_source(api, source, item_information, pack_select=False):
        stream_link = None
        api = api()

        if source["type"] == "torrent":
            try:
                stream_link = api.resolve_magnet(item_information, source, pack_select)
            except CloudMiss as e:
                g.log(f"Cloud miss: {e}", "info")
                source['_cloud_miss'] = True
                # Invalidate this hash in the DB cache so the next scrape cycle
                # doesn't immediately restore it as "confirmed cached" from the
                # stale DB entry — breaking the rescrape → same-sources loop.
                db_key = _DEBRID_PROVIDER_TO_DB_KEY.get(source.get('debrid_provider', ''))
                if db_key and source.get('hash'):
                    try:
                        from resources.lib.database.debridCache import DebridCache
                        DebridCache().set_many_background(
                            [(source['hash'], 'False')], db_key
                        )
                    except Exception:
                        pass
                return None
            except (UnexpectedResponse, FileIdentification) as e:
                g.log(e, "error")
                return None
            except Exception as e:
                g.log(f"Failing Magnet: {source.get('magnet') or source.get('nzb_url', 'unknown')}")
                raise ResolverFailure(source) from e
        elif source["type"] in ["hoster", "cloud"]:
            try:
                stream_link = api.resolve_stream_url({"link": source["url"]})
            except InfringingFile:
                # RD HTTP 451 / error_code=35 — file is DMCA-blocked.
                # Write 7-day block to DebridCache if the source carries a hash
                # (cloud sources may; pure hoster sources typically don't).
                db_key = _DEBRID_PROVIDER_TO_DB_KEY.get(source.get('debrid_provider', ''))
                if db_key and source.get('hash'):
                    try:
                        from resources.lib.database.debridCache import DebridCache
                        DebridCache().set_infringing([source['hash']], db_key)
                    except Exception:
                        pass
                return None
            except (UnexpectedResponse, FileIdentification) as e:
                g.log(e, "error")
                raise ResolverFailure(source) from e

        return stream_link


    @staticmethod
    def reorder_sources(sources, episode_number):
        """
        Bubble the last-played source to position 0 in the sources list.

        Ported from Otaku Testing resolver.reorder_sources().  On each
        successful play we save the winning release title to a setting
        ('resolver.last_played_source').  On the next play for the same
        series we strip hash tokens from both the stored title and each
        candidate, attempt an exact match first, then a fuzzy
        episode-number-position match so that e.g.
        "[SubsPlease] Frieren - 03" matches "[SubsPlease] Frieren - 07"
        when the same episode number position is occupied.

        :param sources: list of source dicts (already sorted by scraper)
        :param episode_number: current episode number (int or str)
        :return: re-ordered sources list (in-place swap, same list object)
        """
        if len(sources) <= 1:
            return sources

        lp = g.get_setting('resolver.last_played_source') or ''
        if not lp or lp == 'None':
            return sources

        # Strip [HASH] tokens (e.g. [E5A85899]) — Otaku pattern
        _hash_re = re.compile(r'\[[0-9A-Fa-f]{8,}\]')
        lp = _hash_re.sub('', lp).strip()
        if not lp:
            return sources

        ep = str(episode_number)
        L  = len(ep)

        # Positions in lp where exactly L consecutive digits appear
        digit_positions = [
            i for i in range(len(lp) - L + 1)
            if lp[i:i + L].isdigit()
        ]

        for idx, source in enumerate(sources):
            rel = str(source.get('release_title', ''))
            rel = _hash_re.sub('', rel).strip()

            # Exact title match
            if rel == lp:
                sources[0], sources[idx] = sources[idx], sources[0]
                g.log(
                    f"ReorderSources: exact match → '{rel[:60]}'",
                    'debug',
                )
                break

            # Fuzzy episode-position match: same title structure, different ep number
            matched = False
            for pos in digit_positions:
                if (rel.startswith(lp[:pos])
                        and rel.endswith(lp[pos + L:])):
                    sources[0], sources[idx] = sources[idx], sources[0]
                    g.log(
                        f"ReorderSources: fuzzy match pos={pos} → '{rel[:60]}'",
                        'debug',
                    )
                    matched = True
                    break
            if matched:
                break

        return sources

    @staticmethod
    def get_hoster_list():
        """
        Fetche
        :return:
        """
        thread_pool = ThreadPool()

        hosters = {"premium": {}, "free": []}

        try:
            if g.get_bool_setting("premiumize.enabled") and g.get_bool_setting("premiumize.hosters"):
                thread_pool.put(Premiumize().get_hosters, hosters)

            if g.get_bool_setting("realdebrid.enabled") and g.get_bool_setting("rd.hosters"):
                thread_pool.put(RealDebrid().get_hosters, hosters)

            if g.get_bool_setting("alldebrid.enabled") and g.get_bool_setting("alldebrid.hosters"):
                thread_pool.put(AllDebrid().get_hosters, hosters)

            if g.get_bool_setting("torbox.enabled") and g.get_bool_setting("torbox.hosters"):
                thread_pool.put(TorBox().get_hosters, hosters)
            thread_pool.wait_completion()
        except ValueError:
            g.log_stacktrace()
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30485))
            return hosters
        return hosters
