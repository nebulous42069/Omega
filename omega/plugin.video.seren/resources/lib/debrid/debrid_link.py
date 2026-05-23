import json
import time
from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.modules.globals import g

DL_TOKEN_KEY = "debridlink.token"
DL_REFRESH_KEY = "debridlink.refresh"
DL_EXPIRY_KEY = "debridlink.expiry"
DL_ENABLED_KEY = "debridlink.enabled"
DL_USERNAME_KEY = "debridlink.username"
DL_STATUS_KEY = "debridlink.premiumstatus"
DL_CLIENT_ID = "sdpBuYFQo6L53s3B4apluw"

# Window property key for the per-session seedbox hash oracle (S168b)
_DL_SEEDBOX_ORACLE_KEY = "seren.dl_seedbox_oracle"


def _extract_oracle_hashes(torrents):
    """Extract info-hashes from a DL /v2/seedbox/list response list.

    Uses the 'hashString' field confirmed from the DL API spec and StremThru
    Go source (SeedboxTorrent.HashString json:"hashString").
    Only includes torrents with downloadPercent == 100 — fully cached in the
    DL pool.  Stalled / in-progress items (downloadPercent < 100) are skipped
    to avoid false-positive CACHED labels at resolve time.

    :param torrents: list of torrent dicts from GET /v2/seedbox/list value[]
    :return: set of lowercase 40-char SHA-1 info-hash strings
    """
    hashes = set()
    for t in torrents:
        if t.get("downloadPercent") != 100:
            continue
        h = t.get("hashString", "")
        if h and len(h) == 40:
            hashes.add(h.lower())
    return hashes


def debridlink_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        import requests

        try:
            response = func(*args, **kwarg)
            if response.status_code in [200, 201]:
                return response

            if response.status_code == 401:
                dl = args[0] if args else None
                if dl and isinstance(dl, DebridLink):
                    dl.refresh_token()
                    response = func(*args, **kwarg)
                    if response.status_code in [200, 201]:
                        return response

            if response.status_code == 429:
                g.log("Debrid-Link Throttling Applied, Sleeping for 2 seconds")
                xbmc.sleep(2 * 1000)
                response = func(*args, **kwarg)

            g.log(
                f"Debrid-Link returned a {response.status_code} "
                f"while requesting {response.url}",
                "warning",
            )
            try:
                error_body = response.json()
                g.log(f"Debrid-Link error body: {error_body}", "warning")
            except Exception:
                pass
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30024).format("Debrid-Link")
            )
            raise

    return wrapper


class DebridLink:
    base_url = "https://debrid-link.com/api/v2/"
    oauth_url = "https://debrid-link.com/api/oauth/"

    def __init__(self):
        self.token = g.get_setting(DL_TOKEN_KEY)
        self.refresh = g.get_setting(DL_REFRESH_KEY)
        self.client_id = DL_CLIENT_ID

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )
        session.mount(
            "https://", HTTPAdapter(max_retries=retries, pool_maxsize=100)
        )
        return session

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": f"Seren/{g.VERSION}",
        }

    # ─── HTTP Methods ───────────────────────────────────────────────────

    @debridlink_guard_response
    def get(self, url, **params):
        if not g.get_bool_setting(DL_ENABLED_KEY):
            return None
        return self.session.get(
            parse.urljoin(self.base_url, url),
            headers=self._headers(),
            params=params,
            timeout=20,
        )

    @debridlink_guard_response
    def post(self, url, post_data=None, **params):
        if not g.get_bool_setting(DL_ENABLED_KEY) or not self.token:
            return None
        return self.session.post(
            parse.urljoin(self.base_url, url),
            headers=self._headers(),
            data=post_data,
            params=params,
            timeout=20,
        )

    @debridlink_guard_response
    def delete(self, url, **params):
        if not g.get_bool_setting(DL_ENABLED_KEY) or not self.token:
            return None
        return self.session.delete(
            parse.urljoin(self.base_url, url),
            headers=self._headers(),
            params=params,
            timeout=20,
        )

    def _extract_value(self, response):
        """Unwrap Debrid-Link response envelope: {"success": bool, "value": ...}"""
        if response is None:
            return None
        data = response.json()
        if isinstance(data, dict) and data.get("success"):
            return data.get("value")
        return None

    def get_json(self, url, **params):
        resp = self.get(url, **params)
        return self._extract_value(resp)

    def post_json(self, url, post_data=None, **params):
        resp = self.post(url, post_data=post_data, **params)
        return self._extract_value(resp)

    def delete_json(self, url, **params):
        resp = self.delete(url, **params)
        return self._extract_value(resp)

    # ─── OAuth Device Code Auth ─────────────────────────────────────────

    def auth(self):
        """Authenticate via OAuth device code flow."""


        url = f"{self.oauth_url}device/code"
        resp = self.session.post(
            url,
            data={"client_id": self.client_id, "scope": "get.post.delete.seedbox get.account"},
            headers={"User-Agent": f"Seren/{g.VERSION}"},
            timeout=20,
        )
        if not resp.ok:
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Failed to initiate Debrid-Link auth.")
            return

        data = resp.json()
        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_url = data["verification_url"]
        interval = data.get("interval", 5)
        expires_in = data["expires_in"]

        try:
            import pyperclip
            pyperclip.copy(user_code)
            copied = True
        except Exception:
            copied = False

        display = (
            f"Go to: [B]{verification_url}[/B][CR]"
            f"Enter code: [B]{user_code}[/B]"
        )
        if copied:
            display += "[CR]Code copied to clipboard"

        progress = xbmcgui.DialogProgress()
        progress.create(f"{g.ADDON_NAME}: Debrid-Link Auth", display)
        progress.update(100)

        timeout = expires_in
        token_url = f"{self.oauth_url}token"

        while timeout > 0:
            xbmc.sleep(interval * 1000)
            timeout -= interval

            if progress.iscanceled():
                progress.close()
                return

            progress.update(int(timeout / expires_in * 100))

            token_resp = self.session.post(
                token_url,
                data={
                    "client_id": self.client_id,
                    "code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"User-Agent": f"Seren/{g.VERSION}"},
                timeout=20,
            )
            if token_resp.ok:
                token_data = token_resp.json()
                if token_data.get("access_token"):
                    progress.close()
                    self.token = token_data["access_token"]
                    self.refresh = token_data.get("refresh_token", "")
                    g.set_setting(DL_TOKEN_KEY, self.token)
                    g.set_setting(DL_REFRESH_KEY, self.refresh)
                    g.set_setting(
                        DL_EXPIRY_KEY,
                        str(int(time.time()) + int(token_data.get("expires_in", 3600))),
                    )
                    self.store_user_info()
                    xbmcgui.Dialog().ok(
                        g.ADDON_NAME, f"Debrid-Link {g.get_language_string(30020)}"
                    )
                    return

        progress.close()

    def refresh_token(self):
        """Refresh the OAuth token."""
        if not self.refresh:
            return
        resp = self.session.post(
            f"{self.oauth_url}token",
            data={
                "client_id": self.client_id,
                "refresh_token": self.refresh,
                "grant_type": "refresh_token",
            },
            headers={"User-Agent": f"Seren/{g.VERSION}"},
            timeout=20,
        )
        if resp and resp.ok:
            data = resp.json()
            if data.get("access_token"):
                self.token = data["access_token"]
                g.set_setting(DL_TOKEN_KEY, self.token)
                g.set_setting(
                    DL_EXPIRY_KEY,
                    str(int(time.time()) + int(data.get("expires_in", 3600))),
                )

    # ─── Account ────────────────────────────────────────────────────────

    def get_user_info(self):
        return self.get_json("account/infos")

    def store_user_info(self):
        user_info = self.get_user_info()
        if user_info is not None:
            username = user_info.get("pseudo", "") or user_info.get("email", "")
            g.set_setting(DL_USERNAME_KEY, username)
            g.set_setting(DL_STATUS_KEY, self.get_account_status().title())

    @staticmethod
    def is_service_enabled():
        return (
            g.get_bool_setting(DL_ENABLED_KEY)
            and g.get_setting(DL_TOKEN_KEY) is not None
            and g.get_setting(DL_TOKEN_KEY) != ""
        )

    def get_account_status(self):
        user_info = self.get_user_info()
        if not isinstance(user_info, dict):
            return "unknown"
        premium_left = user_info.get("premiumLeft", 0)
        if premium_left > 0:
            return "premium"
        return "expired"

    def revoke_auth(self):
        """Remove Debrid-Link authorization after user confirmation."""
        if not self.token:
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Debrid-Link is not currently authorized.")
            return
        if not xbmcgui.Dialog().yesno(
            g.ADDON_NAME, "Remove Debrid-Link authorization?"
        ):
            return
        g.set_setting(DL_TOKEN_KEY, "")
        g.set_setting(DL_REFRESH_KEY, "")
        g.set_setting(DL_USERNAME_KEY, "")
        g.set_setting(DL_STATUS_KEY, "")
        self.token = ""
        self.refresh = ""
        xbmcgui.Dialog().ok(g.ADDON_NAME, "Debrid-Link authorization removed.")

    def account_info_to_dialog(self):
        """
        Fetch account info from Debrid-Link API and display in a select dialog.
        Mirrors Account Manager's DebridLink.account_info_to_dialog() format.
        """
        try:
            user_info = self.get_user_info()
            if not isinstance(user_info, dict):
                xbmcgui.Dialog().ok(g.ADDON_NAME, "Debrid-Link: Could not retrieve account information.")
                return
            premium_left = user_info.get("premiumLeft", 0)
            days_remaining = premium_left // 86400
            status = "Premium" if days_remaining > 0 else "Free / Expired"
            username = user_info.get("pseudo", "") or user_info.get("email", "N/A")
            lines = [
                "Username:  %s" % username,
                "Email:     %s" % user_info.get("email", "N/A"),
                "Status:    %s" % status,
                "Days left: %s" % days_remaining,
            ]
            xbmcgui.Dialog().select("%s: Debrid-Link Account" % g.ADDON_NAME, lines)
        except Exception as e:
            g.log("DL account_info_to_dialog error: %s" % e, "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Debrid-Link: Could not retrieve account information.")



    # ─── Cache Check ────────────────────────────────────────────────────

    def check_cache(self, hash_list):
        """Check which hashes are cached on Debrid-Link.

        NOTE: As of late 2024, Debrid-Link disabled the /v2/seedbox/cached
        endpoint (returns 'endpointDisabled').  Cache checking is handled
        entirely by external_cache.check_dl_external() via Comet only.
        Torrentio was removed in S168a — it accepts DL keys for stream
        resolution but has never implemented DL cache-status detection.
        """
        return {}

    # ─── Seedbox / Torrent Operations ───────────────────────────────────

    def add_magnet(self, magnet):
        """Add a magnet link to the seedbox asynchronously.
        POST /v2/seedbox/add with url=magnet&async=true
        Returns torrent info dict with id, files, etc.
        NOTE: files field is empty in async mode — use add_magnet_sync() in the resolver."""
        return self.post_json(
            "seedbox/add",
            post_data={"url": magnet, "async": "true"},
        )

    def add_magnet_sync(self, magnet):
        """Add a magnet link to the seedbox synchronously.
        POST /v2/seedbox/add with url=magnet (no async flag).
        Used by the resolver so files are populated immediately in the response.
        add_magnet() uses async=true which returns files=[] and causes CloudMiss."""
        return self.post_json(
            "seedbox/add",
            post_data={"url": magnet},
        )

    def torrent_info(self, torrent_id):
        """Get torrent details.
        GET /v2/seedbox/{id}/activity"""
        return self.get_json(f"seedbox/{torrent_id}/activity")

    def list_torrents(self):
        """List all seedbox torrents.
        GET /v2/seedbox/list"""
        return self.get_json("seedbox/list") or []

    # ─── Seedbox-list session oracle (S168b) ────────────────────────────

    def _list_all_torrents_for_oracle(self):
        """Fetch every page of /v2/seedbox/list for the session oracle.

        DL paginates: perPage max=50, page starts at 0.  Loops until the API
        returns an empty page or we reach the stated page-count in the
        pagination envelope.  Hard cap of 20 pages (1,000 torrents) to guard
        against runaway loops on pathological accounts.

        Unlike list_torrents() — which goes through get_json() and discards
        the pagination envelope — this method reads the raw response so it can
        inspect pagination.pages and stop correctly.

        :return: flat list of torrent dicts across all pages
        """
        all_torrents = []
        page = 0
        per_page = 50
        max_pages = 20
        while page < max_pages:
            resp = self.get("seedbox/list", perPage=per_page, page=page)
            if resp is None:
                break
            try:
                data = resp.json()
            except Exception:
                break
            if not isinstance(data, dict) or not data.get("success"):
                break
            page_items = data.get("value") or []
            if isinstance(page_items, list):
                all_torrents.extend(page_items)
            pagination = data.get("pagination") or {}
            total_pages = pagination.get("pages", 1)
            if not page_items or page >= total_pages - 1:
                break
            page += 1
        return all_torrents

    def get_seedbox_oracle_hashes(self):
        """Return the set of info-hashes for all fully-cached DL seedbox torrents.

        Fetches /v2/seedbox/list (all pages) once per Kodi session and stores
        the resulting hash set as a JSON list in the HOME_WINDOW property
        'seren.dl_seedbox_oracle'.  Every subsequent call in the same session
        reads from that property — zero extra API calls.

        Any scraped hash present in this set is 100% confirmed cached: it
        already exists in the user's personal DL seedbox (downloadPercent==100),
        meaning DL will serve it instantly at resolve time.  This catches
        re-watches and recent manual cloud adds that Comet has not yet indexed.

        Side benefit: DebridLinkCloudScraper._fetch_cloud_items() already calls
        list_torrents() for filename-matching.  It also invokes
        _populate_oracle_from_list() so the oracle window property is filled
        from that same fetch — _debridlink_worker then reads the cached property
        and needs no second API call.

        :return: set of lowercase 40-char SHA-1 info-hash strings (empty on failure)
        """
        # Fast path: already populated this Kodi session
        try:
            cached = g.HOME_WINDOW.getProperty(_DL_SEEDBOX_ORACLE_KEY)
            if cached:
                return set(json.loads(cached))
        except Exception:
            pass

        # Fetch from API (all pages) and cache in window property
        try:
            torrents = self._list_all_torrents_for_oracle()
            hashes = _extract_oracle_hashes(torrents)
            try:
                g.HOME_WINDOW.setProperty(_DL_SEEDBOX_ORACLE_KEY, json.dumps(list(hashes)))
            except Exception:
                pass
            g.log(
                f"DL SeedboxOracle: fetched {len(hashes)} completed hashes "
                f"from {len(torrents)} seedbox items (all pages)",
                "info",
            )
            return hashes
        except Exception as e:
            g.log(f"DL SeedboxOracle: fetch failed ({e}) — skipping oracle", "warning")
            return set()

    def _populate_oracle_from_list(self, torrents):
        """Populate the session oracle from an already-fetched seedbox list.

        Called by DebridLinkCloudScraper._fetch_cloud_items() after its own
        list_torrents() call, so the oracle window property is filled without
        a second API round-trip.  No-op if the oracle was already set earlier
        in the session (e.g. _debridlink_worker ran before Tier 0).

        Note: list_torrents() only returns page 0 (≤50 items).  If the account
        has >50 torrents, get_seedbox_oracle_hashes() will fetch all pages when
        called directly; this side-benefit path only covers the first page but
        is still valuable for the common case.

        :param torrents: list of torrent dicts from list_torrents()
        """
        try:
            if g.HOME_WINDOW.getProperty(_DL_SEEDBOX_ORACLE_KEY):
                return  # already populated — don't overwrite
        except Exception:
            pass
        if not isinstance(torrents, list):
            return
        hashes = _extract_oracle_hashes(torrents)
        try:
            g.HOME_WINDOW.setProperty(_DL_SEEDBOX_ORACLE_KEY, json.dumps(list(hashes)))
        except Exception:
            pass
        g.log(
            f"DL SeedboxOracle: populated {len(hashes)} hashes from "
            f"Tier-0 cloud scraper list (no extra API call)",
            "info",
        )

    def delete_torrent(self, torrent_id):
        """Remove a torrent from the seedbox.
        DELETE /v2/seedbox/{id}/remove"""
        result = self.delete_json(f"seedbox/{torrent_id}/remove")
        return result is not None

    def probe_magnet(self, magnet, timeout=5):
        """Probe a single magnet against the DL seedbox to check if it is cached.

        Posts to /v2/seedbox/add with async=true and a short per-request timeout.
        DL returns downloadPercent=100 immediately for hashes already in its
        shared pool — typically 200–400 ms.  For uncached hashes, async=true
        returns in <1 s with downloadPercent=0 (no tracker wait), so the probe
        never blocks the scrape pipeline regardless of the result.

        Callers must delete the returned torrent ID when done:
          - downloadPercent == 100  (cached)  → store ID for post-play cleanup
          - downloadPercent <  100  (not cached) → delete immediately

        :param magnet:  Full magnet URI or bare 40-char info-hash
        :param timeout: Per-request timeout in seconds (default 5)
        :return: dict with keys 'id' and 'is_cached', or None on failure
        :rtype: dict | None
        """
        if not self.token:
            return None
        try:
            resp = self.session.post(
                parse.urljoin(self.base_url, "seedbox/add"),
                headers=self._headers(),
                data={"url": magnet, "async": "true"},
                timeout=timeout,
            )
            if resp.status_code not in (200, 201):
                return None
            data = resp.json()
            if not isinstance(data, dict) or not data.get("success"):
                return None
            torrent = data.get("value") or {}
            torrent_id = torrent.get("id")
            if not torrent_id:
                return None
            is_cached = torrent.get("downloadPercent") == 100
            return {"id": torrent_id, "is_cached": is_cached}
        except Exception:
            return None

    def delete_torrents_background(self, id_list):
        """Delete a list of seedbox torrent IDs in a background daemon thread.

        Mirrors AllDebrid.delete_magnets_background() — used by the speculative
        probe (S168c) to clean up:
          - uncached probe adds immediately after the probe completes
          - cached probe adds after the user plays (via router.py cleanup hook)
          - stale probe adds at the start of the next scrape

        :param id_list: List of DL torrent ID strings to delete
        """
        if not id_list:
            return
        from threading import Thread

        def _delete():
            g.log(
                f"DL SeedboxProbe: background-deleting {len(id_list)} "
                f"probe torrent(s): {id_list}",
                "info",
            )
            for torrent_id in id_list:
                try:
                    self.delete_torrent(torrent_id)
                except Exception as e:
                    g.log(
                        f"DL SeedboxProbe: delete error (id={torrent_id}): {e}",
                        "warning",
                    )
            g.log(
                f"DL SeedboxProbe: done — {len(id_list)} probe torrent(s) removed",
                "info",
            )

        t = Thread(target=_delete)
        t.daemon = True
        t.start()

    def resolve_hoster(self, link):
        """Resolve a download URL. For Debrid-Link, files already have
        direct downloadUrl so this is a passthrough."""
        return link

    def create_transfer(self, magnet):
        """Add magnet to seedbox. Returns torrent_id string or empty string.
        Used by cacheAssist for uncached torrent downloading."""
        result = self.add_magnet(magnet)
        if result and isinstance(result, dict):
            return str(result.get("id", ""))
        return ""
