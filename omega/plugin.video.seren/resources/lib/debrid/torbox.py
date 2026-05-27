from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.modules.globals import g

TB_TOKEN_KEY = "torbox.token"
TB_ENABLED_KEY = "torbox.enabled"
TB_USERNAME_KEY = "torbox.username"
TB_STATUS_KEY = "torbox.premiumstatus"


def torbox_guard_response(func):
    @wraps(func)
    def wrapper(*args, **kwarg):
        import requests

        try:
            response = func(*args, **kwarg)
            if response is None:
                return None
            if response.status_code in [200, 201]:
                return response

            if response.status_code == 429:
                g.log("TorBox Throttling Applied, Sleeping for 1 second")
                xbmc.sleep(1 * 1000)
                response = func(*args, **kwarg)
                if response is None:
                    return None
                if response.status_code in [200, 201]:
                    return response

            g.log(
                f"TorBox returned a {response.status_code} "
                f"while requesting {response.url}",
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(
                g.ADDON_NAME, g.get_language_string(30024).format("TorBox")
            )
            raise

    return wrapper


class TorBox:
    base_url = "https://api.torbox.app/v1/api/"

    def __init__(self):
        self.token = g.get_setting(TB_TOKEN_KEY)

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

    @torbox_guard_response
    def get(self, url, **params):
        if not g.get_bool_setting(TB_ENABLED_KEY):
            return
        return self.session.get(
            parse.urljoin(self.base_url, url),
            headers=self._headers(),
            params=params,
            timeout=20,
        )

    @torbox_guard_response
    def post(self, url, post_data=None, json_data=None, **params):
        if not g.get_bool_setting(TB_ENABLED_KEY) or not self.token:
            return
        return self.session.post(
            parse.urljoin(self.base_url, url),
            headers=self._headers(),
            data=post_data,
            json=json_data,
            params=params,
            timeout=20,
        )

    def _extract_data(self, response, url=""):
        """Unwrap TorBox response envelope: {"success": bool, "data": ...}
        POV skips unwrapping for 'control' paths (delete operations)
        where the raw success/error response is needed."""
        if response is None:
            return None
        if isinstance(response, dict) and "data" in response and "success" in response:
            if "control" not in url:
                return response["data"]
        return response

    def get_json(self, url, **params):
        resp = self.get(url, **params)
        if resp is None:
            return None
        return self._extract_data(resp.json(), url)

    def post_json(self, url, post_data=None, json_data=None, **params):
        resp = self.post(url, post_data=post_data, json_data=json_data, **params)
        if resp is None:
            return None
        return self._extract_data(resp.json(), url)

    # ─── Auth (Direct API Token Entry) ────────────────────────────────

    def auth(self):
        """Authenticate by entering TorBox API token directly.
        User gets their token from https://torbox.app/settings → API section.
        Avoids device code flow which can be blocked by antivirus software."""


        # Prompt user to enter API token
        keyboard = xbmc.Keyboard(
            "", "Enter TorBox API Token (from torbox.app/settings)"
        )
        keyboard.doModal()

        if not keyboard.isConfirmed():
            return

        token = keyboard.getText().strip()
        if not token:
            xbmcgui.Dialog().ok(g.ADDON_NAME, "No token entered.")
            return

        # Validate the token by calling /user/me
        try:
            resp = self.session.get(
                parse.urljoin(self.base_url, "user/me"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": f"Seren/{g.VERSION}",
                },
                timeout=20,
            )
            if not resp.ok:
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME,
                    f"TorBox rejected the token (HTTP {resp.status_code}). "
                    "Check your token and try again.",
                )
                return

            data = resp.json()
            if not data.get("success"):
                xbmcgui.Dialog().ok(
                    g.ADDON_NAME, "TorBox API returned an error. Check your token."
                )
                return

        except Exception as e:
            g.log(f"TorBox auth validation failed: {e}", "error")
            xbmcgui.Dialog().ok(
                g.ADDON_NAME,
                f"Could not connect to TorBox:[CR][CR]{e}",
            )
            return

        # Token is valid — save it
        self.token = token
        g.set_setting(TB_TOKEN_KEY, token)
        self.store_user_info()
        xbmcgui.Dialog().ok(
            g.ADDON_NAME, f"TorBox {g.get_language_string(30020)}"
        )

    # ─── Account ────────────────────────────────────────────────────────

    def get_user_info(self):
        return self.get_json("user/me")

    def store_user_info(self):
        resp = self.session.get(
            parse.urljoin(self.base_url, "user/me"),
            headers=self._headers(),
            timeout=20,
        )
        if resp and resp.ok:
            user_info = self._extract_data(resp.json(), "user/me")
            if isinstance(user_info, dict):
                g.set_setting(TB_USERNAME_KEY, user_info.get("email", ""))
                g.set_setting(TB_STATUS_KEY, self.get_account_status(user_info).title())

    @staticmethod
    def is_service_enabled():
        return (
            g.get_bool_setting(TB_ENABLED_KEY)
            and g.get_setting(TB_TOKEN_KEY) is not None
            and g.get_setting(TB_TOKEN_KEY) != ""
        )

    def get_account_status(self, user_info=None):
        if user_info is None:
            user_info = self.get_user_info()
        if not isinstance(user_info, dict):
            return "unknown"

        plan = user_info.get("plan", -1)
        if plan == 0:
            return "free"

        # Check expiry for premium plans
        premium_expires = user_info.get("premium_expires_at")
        if premium_expires:
            try:
                from datetime import datetime, timezone

                expires = datetime.fromisoformat(
                    premium_expires.replace("Z", "+00:00")
                )
                if expires < datetime.now(timezone.utc):
                    return "expired"
            except (ValueError, TypeError):
                pass

        return {1: "essential", 2: "pro", 3: "standard"}.get(plan, "unknown")

    # ─── Cache Check ────────────────────────────────────────────────────


    def revoke_auth(self):
        """Remove TorBox authorization after user confirmation."""
        if not self.token:
            xbmcgui.Dialog().ok(g.ADDON_NAME, "TorBox is not currently authorized.")
            return
        if not xbmcgui.Dialog().yesno(
            g.ADDON_NAME, "Remove TorBox authorization?"
        ):
            return
        g.set_setting(TB_TOKEN_KEY, "")
        g.set_setting(TB_USERNAME_KEY, "")
        g.set_setting(TB_STATUS_KEY, "")
        self.token = ""
        xbmcgui.Dialog().ok(g.ADDON_NAME, "TorBox authorization removed.")

    def account_info_to_dialog(self):
        """
        Fetch account info from TorBox API and display in a select dialog.
        Mirrors Account Manager's TorBox.account_info_to_dialog() format.
        Bypasses the enabled-check guard so it works even when torbox.enabled=false
        (e.g. immediately after auth before the user re-enables the service).
        """
        from datetime import datetime, timezone
        try:
            resp = self.session.get(
                parse.urljoin(self.base_url, "user/me"),
                headers=self._headers(),
                timeout=20,
            )
            if not (resp and resp.ok):
                xbmcgui.Dialog().ok(g.ADDON_NAME, "TorBox: Could not retrieve account information.")
                return
            user_info = self._extract_data(resp.json(), "user/me")
            if not isinstance(user_info, dict):
                xbmcgui.Dialog().ok(g.ADDON_NAME, "TorBox: Could not retrieve account information.")
                return
            plan_names = {0: "Free", 1: "Essential", 2: "Pro", 3: "Standard"}
            plan = user_info.get("plan", -1)
            plan_str = plan_names.get(plan, "Unknown")
            premium_expires = user_info.get("premium_expires_at", "")
            if premium_expires:
                try:
                    expires = datetime.fromisoformat(premium_expires.replace("Z", "+00:00"))
                    days_remaining = (expires - datetime.now(timezone.utc)).days
                    expires_str = expires.strftime("%A, %B %d, %Y")
                except (ValueError, TypeError):
                    days_remaining = "N/A"
                    expires_str = premium_expires
            else:
                days_remaining = "N/A"
                expires_str = "N/A"
            lines = [
                "Email:     %s" % user_info.get("email", "N/A"),
                "Plan:      %s" % plan_str,
                "Status:    %s" % self.get_account_status(user_info).capitalize(),
                "Expires:   %s" % expires_str,
                "Days left: %s" % days_remaining,
            ]
            xbmcgui.Dialog().select("%s: TorBox Account" % g.ADDON_NAME, lines)
        except Exception as e:
            g.log("TB account_info_to_dialog error: %s" % e, "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, "TorBox: Could not retrieve account information.")


    def check_hash(self, hash_list):
        """Check which hashes are cached on TorBox.
        Called by TorrentCacheCheck._torbox_worker() in getSources.py.
        Returns a list of cached hash strings.

        Uses POST with JSON body (POV's approach) — handles large hash lists
        better than GET with query params (Otaku's approach)."""
        result = self.post_json(
            "torrents/checkcached",
            json_data={"hashes": hash_list},
            format="list",
        )
        if not result or not isinstance(result, list):
            return []
        # Response is list of dicts with 'hash' key: [{"hash": "abc..."}, ...]
        return [i["hash"] for i in result if isinstance(i, dict) and "hash" in i]

    # ─── Torrent Operations ─────────────────────────────────────────────

    def add_magnet(self, magnet):
        """Add a magnet link. Returns dict with 'torrent_id' on success."""
        return self.post_json(
            "torrents/createtorrent",
            post_data={"magnet": magnet, "seed": 3, "allow_zip": "false"},
        )

    def torrent_info(self, torrent_id):
        """Get torrent details including file list.
        Returns dict with 'files', 'download_state', etc."""
        return self.get_json("torrents/mylist", id=torrent_id)

    def list_torrents(self):
        """List all torrents in user's cloud."""
        return self.get_json("torrents/mylist") or []

    def delete_torrent(self, torrent_id):
        """Delete a torrent from cloud.
        Note: 'control' in URL path means _extract_data keeps the raw response."""
        result = self.post_json(
            "torrents/controltorrent",
            json_data={"torrent_id": torrent_id, "operation": "delete"},
        )
        if isinstance(result, dict):
            return result.get("success", False)
        return False

    def request_download_link(self, torrent_id, file_id):
        """Get a streamable download link for a specific file.
        Uses cached IP lookup for better CDN routing."""
        from resources.lib.debrid.debrid_utils import get_user_ip

        params = {
            "token": self.token,
            "torrent_id": torrent_id,
            "file_id": file_id,
        }
        user_ip = get_user_ip()
        if user_ip:
            params["user_ip"] = user_ip
        return self.get_json("torrents/requestdl", **params)

    def resolve_hoster(self, link):
        """Resolve a 'torrent_id,file_id' composite string into a download URL.
        This matches the interface used by the TorBoxResolver."""
        torrent_id, file_id = str(link).split(",")
        return self.request_download_link(int(torrent_id), int(file_id))

    def create_transfer(self, magnet):
        """Add magnet to cloud. Returns torrent_id string or empty string.
        Used by cacheAssist for uncached torrent downloading."""
        result = self.add_magnet(magnet)
        if result and isinstance(result, dict):
            return str(result.get("torrent_id", ""))
        return ""

    # ─── Hoster / WebDL Operations ──────────────────────────────────────

    def get_hosters(self, hosters):
        """Fetch supported hoster domains from TorBox and update the hosters dict.
        Called by Resolver.get_hoster_list() to register TorBox as a hoster provider.
        TorBox API: GET /webdl/hosters → list of {name, domains[], status, type}"""
        host_list = self._fetch_hoster_list()
        if host_list and isinstance(host_list, list):
            hosters["premium"]["torbox"] = [
                (d, d.split(".")[0])
                for hoster in host_list
                if hoster.get("status", False)
                for d in hoster.get("domains", [])
            ]
        else:
            hosters["premium"]["torbox"] = []

    def _fetch_hoster_list(self):
        """Get the list of supported hosters from TorBox API."""
        return self.get_json("webdl/hosters")

    def create_webdl(self, url):
        """Create a web download from a hoster URL.
        Returns dict with 'webdl_id' on success."""
        return self.post_json(
            "webdl/createwebdownload",
            post_data={"link": url},
        )

    def webdl_info(self, webdl_id):
        """Get web download details including file list."""
        return self.get_json("webdl/mylist", id=webdl_id)

    def delete_webdl(self, webdl_id):
        """Delete a web download."""
        result = self.post_json(
            "webdl/controlwebdownload",
            json_data={"webdl_id": webdl_id, "operation": "delete"},
        )
        if isinstance(result, dict):
            return result.get("success", False)
        return False

    def request_webdl_link(self, webdl_id, file_id):
        """Get a streamable download link for a web download file."""
        from resources.lib.debrid.debrid_utils import get_user_ip

        params = {
            "token": self.token,
            "web_id": webdl_id,
            "file_id": file_id,
        }
        user_ip = get_user_ip()
        if user_ip:
            params["user_ip"] = user_ip
        return self.get_json("webdl/requestdl", **params)

    def resolve_hoster_url(self, url):
        """Resolve a hoster URL into a streamable download link via TorBox WebDL.
        Creates a web download, polls until ready, then gets the stream URL.
        Used by Seren's hoster pipeline for URL-based sources."""
        try:
            result = self.create_webdl(url)
            if not result or "webdl_id" not in result:
                g.log(f"TorBox WebDL: Failed to create download for {url}", "warning")
                return None

            webdl_id = result["webdl_id"]

            # Poll until download is ready (max 30 seconds)
            for _ in range(30):
                xbmc.sleep(1000)
                info = self.webdl_info(webdl_id)
                if not info:
                    break
                if info.get("download_finished"):
                    files = info.get("files", [])
                    if files:
                        file_id = files[0]["id"]
                        stream_url = self.request_webdl_link(webdl_id, file_id)
                        return stream_url
                    break
                state = info.get("download_state", "")
                if state in ("error", "failed"):
                    break

            # Cleanup on failure
            self.delete_webdl(webdl_id)
            return None
        except Exception as e:
            g.log(f"TorBox WebDL resolve error: {e}", "error")
            return None

    # ─── Usenet Operations ──────────────────────────────────────────────

    def list_usenet(self):
        """List all usenet downloads in user's cloud."""
        return self.get_json("usenet/mylist") or []

    def usenet_info(self, usenet_id):
        """Get usenet download details including file list."""
        return self.get_json("usenet/mylist", id=usenet_id)

    def delete_usenet(self, usenet_id):
        """Delete a usenet download from cloud."""
        result = self.post_json(
            "usenet/controlusenetdownload",
            json_data={"usenet_id": usenet_id, "operation": "delete"},
        )
        if isinstance(result, dict):
            return result.get("success", False)
        return False

    def request_usenet_link(self, usenet_id, file_id):
        """Get a streamable download link for a usenet file."""
        from resources.lib.debrid.debrid_utils import get_user_ip

        params = {
            "token": self.token,
            "usenet_id": usenet_id,
            "file_id": file_id,
        }
        user_ip = get_user_ip()
        if user_ip:
            params["user_ip"] = user_ip
        return self.get_json("usenet/requestdl", **params)

    def add_nzb(self, nzb_url, name=""):
        """Create a usenet download from an NZB URL.
        Returns dict with 'usenetdownload_id' on success."""
        post_data = {"link": nzb_url}
        if name:
            post_data["name"] = name
        return self.post_json(
            "usenet/createusenetdownload",
            post_data=post_data,
        )

    def search_usenet(self, imdb_id, season=None, episode=None):
        """Search TorBox's usenet index by IMDB ID.
        Uses the separate search-api.torbox.app endpoint.
        Returns list of NZB result dicts with 'cached' status pre-checked.

        Reference: POV torboxnews.py search() method."""
        url = f"https://search-api.torbox.app/usenet/imdb:{imdb_id}"
        params = {
            "check_cache": "true",
            "check_owned": "true",
            "search_user_engines": "true",
        }
        if season is not None and episode is not None:
            params["season"] = int(season)
            params["episode"] = int(episode)

        resp = self.get(url, **params)
        if resp is None:
            return []
        try:
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            return data.get("nzbs", []) if isinstance(data, dict) else []
        except Exception as e:
            g.log(f"TorBox usenet search error: {e}", "warning")
            return []

    def resolve_usenet(self, link):
        """Resolve a 'usenet_id,file_id' composite string into a download URL."""
        usenet_id, file_id = str(link).split(",")
        return self.request_usenet_link(int(usenet_id), int(file_id))

    # ─── Cloud Listing (All Types) ─────────────────────────────────────

    def list_webdl(self):
        """List all web downloads in user's cloud."""
        return self.get_json("webdl/mylist") or []

    def resolve_webdl(self, link):
        """Resolve a 'webdl_id,file_id' composite string into a download URL."""
        webdl_id, file_id = str(link).split(",")
        return self.request_webdl_link(int(webdl_id), int(file_id))

    def resolve_by_type(self, link, media_type="torrent"):
        """Resolve a composite link string using the appropriate API endpoint.
        media_type: 'torrent', 'usenet', or 'webdl'."""
        if media_type == "usenet":
            return self.resolve_usenet(link)
        elif media_type == "webdl":
            return self.resolve_webdl(link)
        else:
            return self.resolve_hoster(link)
