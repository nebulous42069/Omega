import time
from functools import cached_property
from functools import wraps
from urllib import parse

import xbmc
import xbmcgui

from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.modules.globals import g

AD_AUTH_KEY = "alldebrid.apikey"
AD_ENABLED_KEY = "alldebrid.enabled"


def alldebrid_guard_response(func):
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
                g.log('Alldebrid Throttling Applied, Sleeping for 1 seconds')
                xbmc.sleep(1 * 1000)
                response = func(*args, **kwarg)
                if response is None:
                    return None
                # Check the retry response — if it succeeded, return it.
                # Previous code fell through to the log+return-None path even
                # on a successful retry, silently discarding the valid response.
                if response.status_code in [200, 201]:
                    return response

            g.log(
                f"AllDebrid returned a {response.status_code} "
                f"({AllDebrid.http_codes.get(response.status_code, 'Unknown Error')}): "
                f"while requesting {response.url}",
                "warning",
            )
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception:
            xbmcgui.Dialog().notification(g.ADDON_NAME, g.get_language_string(30024).format("AllDebrid"))
            raise

    return wrapper


class AllDebrid:
    base_url = "https://api.alldebrid.com/v4/"

    http_codes = {
        200: "Success",
        400: "Bad Request, The request was unacceptable, often due to missing a required parameter",
        401: "Unauthorized",
        403: "Forbidden — token invalid or account not premium",
        404: "Not Found, Api endpoint doesn't exist",
        405: "Method Not Allowed",
        408: "Request Timeout",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        522: "Connection Timed Out (Cloudflare)",
        524: "A Timeout Occurred (Cloudflare)",
        530: "Site is Frozen (Cloudflare)",
    }

    def __init__(self):
        self.apikey = g.get_setting(AD_AUTH_KEY)

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    @alldebrid_guard_response
    def get(self, url, **params):
        if not g.get_bool_setting(AD_ENABLED_KEY):
            return

        reauth = params.pop("reauth", None)
        apikey = None if reauth else self.apikey

        full_url = parse.urljoin(self.base_url, url)
        # AllDebrid v4.1 is required for magnet/status — v4 returns a different
        # response format missing the 'magnets' key.
        # Reference: FenLight, Umbrella, POV all use v4.1 for this endpoint.
        if "magnet/status" in url:
            full_url = full_url.replace("/v4/", "/v4.1/")

        # As of 15/01/2025 AllDebrid API requires Authorization: Bearer header.
        # agent and apikey query params are no longer accepted.
        headers = {"Authorization": f"Bearer {apikey}"} if apikey else {}
        return self.session.get(full_url, params=params, headers=headers)

    def get_json(self, url, **params):
        """GET request returning parsed JSON data, or {} if the request failed."""
        response = self.get(url, **params)
        if not response:
            return {}
        return self._extract_data(response.json())

    @alldebrid_guard_response
    def post(self, url, post_data=None, **params):
        if not g.get_bool_setting(AD_ENABLED_KEY) or not self.apikey:
            return
        # As of 15/01/2025 AllDebrid API requires Authorization: Bearer header.
        headers = {"Authorization": f"Bearer {self.apikey}"}
        return self.session.post(parse.urljoin(self.base_url, url), data=post_data, params=params, headers=headers)

    def post_json(self, url, post_data=None, **params):
        """POST request returning parsed JSON data, or {} if the request failed."""
        response = self.post(url, post_data, **params)
        if not response:
            return {}
        return self._extract_data(response.json())

    def _extract_data(self, response):
        if isinstance(response, dict) and response.get("status") == "error":
            err = response.get("error", {})
            code = err.get("code", "UNKNOWN") if isinstance(err, dict) else str(err)
            msg  = err.get("message", "") if isinstance(err, dict) else ""
            g.log(f"AllDebrid API error: {code} — {msg}", "warning")
        return response["data"] if "data" in response else response
    def auth(self):
        resp = self.get_json("pin/get", reauth=True)
        if not resp or "expires_in" not in resp:
            xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30024).format("AllDebrid"))
            return
        expiry = pin_ttl = int(resp["expires_in"])
        auth_complete = False
        auth_check = None
        tools.copy2clip(resp["pin"])
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30334)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string(resp["base_url"])),
                    line2=g.get_language_string(30019).format(g.color_string(resp["pin"])),
                    line3=g.get_language_string(30047),
                ),
            )

            # Seems the All Debrid servers need some time do something with the pin before polling
            # Polling to early will cause an invalid pin error
            xbmc.sleep(5 * 1000)
            progress_dialog.update(100)

            while not auth_complete and expiry > 0 and not progress_dialog.iscanceled():
                auth_check = self.get_json("pin/check", check=resp["check"], pin=resp["pin"])
                if not auth_check or "activated" not in auth_check:
                    xbmc.sleep(1 * 1000)
                    continue
                if auth_check["activated"]:
                    auth_complete = True
                    break
                else:
                    expiry = int(auth_check["expires_in"])
                    progress_percent = 100 - int((float(pin_ttl - expiry) / pin_ttl) * 100)
                    progress_dialog.update(progress_percent)
                    xbmc.sleep(1 * 1000)

            progress_dialog.close()

            if auth_complete and not progress_dialog.iscanceled() and auth_check is not None:
                g.set_setting(AD_AUTH_KEY, auth_check["apikey"])
                self.apikey = auth_check["apikey"]
                self.store_user_info()
        finally:
            del progress_dialog

        if auth_complete:
            xbmcgui.Dialog().ok(g.ADDON_NAME, f"AllDebrid {g.get_language_string(30020)}")
        else:
            return

    def get_user_info(self):
        result = self.get_json("user")
        if not isinstance(result, dict):
            return {}
        return result.get("user", {})

    def store_user_info(self):
        user_information = self.get_user_info()
        if user_information:
            g.set_setting("alldebrid.username", user_information.get("username", ""))
            g.set_setting("alldebrid.premiumstatus", self.get_account_status().title())

    def upload_magnet(self, magnet_uri):
        """
        Upload a single magnet URI to the user's AD account.

        Call only at resolution time for the ONE source the user selected.
        Never call in a loop for bulk cache checking — that creates one transfer
        per hash, pollutes the account, and risks hitting the 1,000-transfer limit.

        Prefer the full magnet URI (magnet:?xt=urn:btih:HASH&dn=...&tr=...) over
        a bare hash — AD resolves faster when dn= and tr= fields are present.

        :param magnet_uri: Full magnet URI or bare 40-char info-hash
        :return: API response dict with 'magnets' key, or None on failure
        """
        result = self.get_json("magnet/upload", magnet=magnet_uri)
        if not isinstance(result, dict) or "magnets" not in result:
            g.log(
                f"AD upload_magnet: unexpected response (no 'magnets' key) — "
                f"account may not be premium. Response: {str(result)[:200]}",
                "warning",
            )
            return None
        return result

    def upload_magnet_batch(self, magnet_list):
        """
        Upload multiple magnet URIs in a single POST to AD's magnet/upload endpoint.

        AD returns 'ready: true' for each magnet that is already cached — no
        separate cache-check call needed. Uncached magnets return 'ready: false'
        and should be deleted immediately to avoid cluttering the transfer list.

        :param magnet_list: List of full magnet URIs or 40-char info-hashes
        :type magnet_list: list[str]
        :return: List of dicts — {hash, id, ready, name} — one per uploaded magnet
        :rtype: list[dict]
        """
        if not magnet_list:
            return []

        # Build form data: magnets[]=uri1&magnets[]=uri2 (repeated keys)
        post_data = [('magnets[]', m) for m in magnet_list]
        response = self.post('magnet/upload', post_data=post_data)
        if not response:
            return []

        try:
            data = response.json()
            if data.get('status') == 'error':
                err  = data.get('error', {})
                code = err.get('code', 'UNKNOWN') if isinstance(err, dict) else str(err)
                msg  = err.get('message', '') if isinstance(err, dict) else ''
                g.log(
                    f"AD upload_magnet_batch: API error {code} — {msg}. "
                    f"Account may not be premium.",
                    "warning",
                )
                return []
            magnets = data.get('data', {}).get('magnets', [])
            return [
                {
                    'hash': m.get('hash', '').lower(),
                    'id': m.get('id'),
                    'ready': bool(m.get('ready', False)),
                    'name': m.get('name', ''),
                }
                for m in magnets
                if m.get('id')
            ]
        except Exception as e:
            g.log(f"AD upload_magnet_batch parse error: {e}", "warning")
            return []

    def delete_magnets_background(self, id_list):
        """
        Delete a list of magnet IDs from AD in a background daemon thread.

        Used to clean up uncached uploads (ready=False) immediately after a
        batch check, and to clean up other cached uploads after successful play.

        :param id_list: List of AD magnet IDs to delete
        :type id_list: list[int]
        """
        if not id_list:
            return
        from threading import Thread

        def _delete():
            g.log(
                f"AD delete_magnets_background: deleting {len(id_list)} uncached upload(s) "
                f"{id_list}",
                "info",
            )
            for magnet_id in id_list:
                try:
                    self.delete_magnet(magnet_id)
                except Exception as e:
                    g.log(f"AD delete_magnets_background error (id={magnet_id}): {e}", "warning")
            g.log(
                f"AD delete_magnets_background: done — {len(id_list)} upload(s) removed from AD",
                "info",
            )

        t = Thread(target=_delete)
        t.daemon = True
        t.start()

    @staticmethod
    def _flatten_files(file_list):
        """
        Recursively flatten AD's nested file tree into a flat list of leaf nodes.

        AD's v4.1 magnet/status returns files as a nested structure:
            {'n': 'FolderName', 'e': [children]}   <- directory node
            {'n': 'movie.mkv', 'l': 'https://...', 's': 1234567}  <- leaf node

        Leaf nodes carry 'l' (link) and 's' (size) instead of 'e' (entries).
        Mirrors POV's AllDebridAPI.flatten_magnet_files() exactly.

        :param file_list: Raw 'files' value from magnet/status response
        :type file_list: list
        :return: Flat list of leaf file dicts
        :rtype: list[dict]
        """
        out = []
        for item in file_list or []:
            if not isinstance(item, dict):
                continue
            if 'e' in item:
                out.extend(AllDebrid._flatten_files(item['e']))
            else:
                out.append(item)
        return out

    @use_cache(1)
    def update_relevant_hosters(self):
        return self.get_json("hosts")

    def get_hosters(self, hosters):
        host_list = self.update_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["all_debrid"] = [
                (d, d.split(".")[0])
                for l in host_list["hosts"].values()
                if "status" in l and l["status"]
                for d in l["domains"]
            ]
        else:
            g.log_stacktrace()
            hosters["premium"]["all_debrid"] = []

    def resolve_hoster(self, url):
        from resources.lib.debrid.debrid_utils import get_user_ip

        params = {"link": url}
        user_ip = get_user_ip()
        if user_ip:
            params["ip"] = user_ip
        try:
            resolve = self.get_json("link/unlock", **params)
            return resolve["link"]
        except (KeyError, TypeError, AttributeError):
            return None

    def magnet_status(self, magnet_id):
        result = self.get_json("magnet/status", id=magnet_id) if magnet_id else self.get_json("magnet/status")
        return result if isinstance(result, dict) else {}

    def saved_magnets(self):
        result = self.get_json("magnet/status")
        if not isinstance(result, dict):
            return []
        return result.get('magnets', [])

    def delete_magnet(self, magnet_id):
        return self.get_json("magnet/delete", id=magnet_id)

    def saved_links(self):
        result = self.get_json("user/links")
        return result if isinstance(result, dict) else {}

    def delete_link(self, link):
        """Delete a saved link from user's account."""
        return self.get_json("link/delete", link=link)

    @staticmethod
    def is_service_enabled():
        return g.get_bool_setting(AD_ENABLED_KEY) and g.get_setting(AD_AUTH_KEY) is not None

    def get_account_status(self, user_info=None):
        if user_info is None:
            user_info = self.get_user_info()
        if not isinstance(user_info, dict):
            return "unknown"

        premium = user_info.get("isPremium")
        premium_until = user_info.get("premiumUntil", 0)
        subscribed = user_info.get("isSubscribed")
        trial = user_info.get("isTrial")

        if premium and premium_until > time.time():
            return "premium"
        elif subscribed:
            return "subscribed"
        elif trial:
            return "trial"
        else:
            return "unknown"


    def revoke_auth(self):
        """Remove AllDebrid authorization after user confirmation."""
        if not g.get_setting(AD_AUTH_KEY):
            xbmcgui.Dialog().ok(g.ADDON_NAME, "AllDebrid is not currently authorized.")
            return
        if not xbmcgui.Dialog().yesno(
            g.ADDON_NAME, "Remove AllDebrid authorization?"
        ):
            return
        g.set_setting(AD_AUTH_KEY, "")
        g.set_setting("alldebrid.username", "")
        g.set_setting("alldebrid.premiumstatus", "")
        xbmcgui.Dialog().ok(g.ADDON_NAME, "AllDebrid authorization removed.")

    def account_info_to_dialog(self):
        """
        Fetch account info from AllDebrid API and display in a select dialog.
        Mirrors Account Manager's AllDebrid.account_info_to_dialog() format.
        Bypasses the enabled-check guard so it works even when alldebrid.enabled=false.
        """
        from datetime import datetime
        try:
            full_url = parse.urljoin(self.base_url, "user")
            headers = {"Authorization": "Bearer %s" % self.apikey} if self.apikey else {}
            resp = self.session.get(full_url, headers=headers, timeout=20)
            if not (resp and resp.ok):
                xbmcgui.Dialog().ok(g.ADDON_NAME, "AllDebrid: Could not retrieve account information.")
                return
            data = self._extract_data(resp.json())
            user_info = data.get("user", {}) if isinstance(data, dict) else {}
            if not isinstance(user_info, dict) or not user_info:
                xbmcgui.Dialog().ok(g.ADDON_NAME, "AllDebrid: Could not retrieve account information.")
                return
            premium_until = user_info.get("premiumUntil", 0)
            if premium_until:
                expires = datetime.fromtimestamp(float(premium_until))
                days_remaining = (expires - datetime.today()).days
                expires_str = expires.strftime("%A, %B %d, %Y")
            else:
                days_remaining = "N/A"
                expires_str = "N/A"
            lines = [
                "Username:  %s" % user_info.get("username", "N/A"),
                "Email:     %s" % user_info.get("email", "N/A"),
                "Status:    %s" % self.get_account_status(user_info).capitalize(),
                "Expires:   %s" % expires_str,
                "Days left: %s" % days_remaining,
            ]
            xbmcgui.Dialog().select("%s: AllDebrid Account" % g.ADDON_NAME, lines)
        except Exception as e:
            g.log("AD account_info_to_dialog error: %s" % e, "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, "AllDebrid: Could not retrieve account information.")

