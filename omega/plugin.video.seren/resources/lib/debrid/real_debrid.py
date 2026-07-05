import time
from functools import cached_property

import xbmc
import xbmcgui

from resources.lib.common import source_utils
from resources.lib.common import tools
from resources.lib.database.cache import use_cache
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.exceptions import UnexpectedResponse
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
import os

RD_AUTH_KEY = "rd.auth"
RD_STATUS_KEY = "rd.premiumstatus"
RD_REFRESH_KEY = "rd.refresh"
RD_EXPIRY_KEY = "rd.expiry"
RD_SECRET_KEY = "rd.secret"
RD_CLIENT_ID_KEY = "rd.client_id"
RD_USERNAME_KEY = "rd.username"
RD_AUTH_CLIENT_ID = "X245A4XAIBGVM"


class RealDebrid:
    def __init__(self):
        self.oauth_url = "https://api.real-debrid.com/oauth/v2/"
        self.device_code_url = "device/code?{}"
        self.device_credentials_url = "device/credentials?{}"
        self.token_url = "token"
        self.device_code = ""
        self.oauth_timeout = 0
        self.oauth_time_step = 0
        self.base_url = "https://api.real-debrid.com/rest/1.0/"
        self.cache_check_results = {}
        self._load_settings()

    @cached_property
    def session(self):
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3 import Retry

        session = requests.Session()
        # 429 is intentionally excluded from status_forcelist — auto-retrying on
        # rate-limit responses amplifies the problem. check_cache_batch handles
        # 429/403 manually and breaks early instead of burning retries.
        retries = Retry(
            total=5,
            backoff_factor=0.1,  # matches Umbrella/POV/AD/TB/DL pattern; more retries, less dead time
            status_forcelist=[500, 502, 503, 504],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_maxsize=100))
        return session

    def _auth_loop(self):
        url = f"client_id={RD_AUTH_CLIENT_ID}&code={self.device_code}"
        url = self.oauth_url + self.device_credentials_url.format(url)
        response = self.session.get(url).json()
        if "error" not in response and response.get("client_secret"):
            try:
                g.set_setting(RD_CLIENT_ID_KEY, response["client_id"])
                g.set_setting(RD_SECRET_KEY, response["client_secret"])
                self.client_secret = response["client_secret"]
                self.client_id = response["client_id"]
                return True
            except Exception:
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30065))
                raise
        return False

    def auth(self):
        url = f"client_id={self.client_id}&new_credentials=yes"
        url = self.oauth_url + self.device_code_url.format(url)
        response = self.session.get(url).json()
        tools.copy2clip(response["user_code"])
        success = False
        try:
            progress_dialog = xbmcgui.DialogProgress()
            progress_dialog.create(
                f"{g.ADDON_NAME}: {g.get_language_string(30017)}",
                tools.create_multiline_message(
                    line1=g.get_language_string(30018).format(g.color_string("https://real-debrid.com/device")),
                    line2=g.get_language_string(30019).format(g.color_string(response["user_code"])),
                    line3=g.get_language_string(30047),
                ),
            )
            self.oauth_timeout = int(response["expires_in"])
            token_ttl = int(response["expires_in"])
            self.oauth_time_step = int(response["interval"])
            self.device_code = response["device_code"]
            progress_dialog.update(100)
            while not success and token_ttl > 0 and not progress_dialog.iscanceled():
                xbmc.sleep(1000)
                if token_ttl % self.oauth_time_step == 0:
                    success = self._auth_loop()
                progress_percent = int(float((token_ttl * 100) / self.oauth_timeout))
                progress_dialog.update(progress_percent)
                token_ttl -= 1
            progress_dialog.close()
        finally:
            del progress_dialog

        if success:
            self.token_request()

            user_information = self.get_url("user")
            if user_information and user_information.get("type") != "premium":
                xbmcgui.Dialog().ok(g.ADDON_NAME, g.get_language_string(30194))

    def token_request(self):
        if not self.client_secret:
            return

        url = self.oauth_url + self.token_url
        response = self.session.post(
            url,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": self.device_code,
                "grant_type": "http://oauth.net/grant_type/device/1.0",
            },
        ).json()
        self._save_settings(response)
        self._save_user_status()
        xbmcgui.Dialog().ok(g.ADDON_NAME, f"Real Debrid {g.get_language_string(30020)}")
        g.log("Authorised Real Debrid successfully", "info")

    def _save_settings(self, response):
        self.token = response["access_token"]
        self.refresh = response["refresh_token"]
        self.expiry = time.time() + int(response["expires_in"])
        g.set_setting(RD_AUTH_KEY, self.token)
        g.set_setting(RD_REFRESH_KEY, self.refresh)
        g.set_setting(RD_EXPIRY_KEY, self.expiry)

    def _save_user_status(self):
        user_info = self.get_url("user")
        username = user_info.get("username") if user_info else ""
        status = self.get_account_status().title()
        g.set_setting(RD_USERNAME_KEY, username)
        g.set_setting(RD_STATUS_KEY, status)

    def _load_settings(self):
        self.client_id = g.get_setting("rd.client_id", RD_AUTH_CLIENT_ID)
        self.token = g.get_setting(RD_AUTH_KEY)
        self.refresh = g.get_setting(RD_REFRESH_KEY)
        self.expiry = g.get_float_setting(RD_EXPIRY_KEY)
        self.client_secret = g.get_setting(RD_SECRET_KEY)

    @staticmethod
    def _handle_error(response):
        g.log(f"Real Debrid API return a {response.status_code} response")
        g.log(response.text)
        g.log(response.request.url)

    def _is_response_ok(self, response):
        if response.ok:
            return True
        self._handle_error(response)
        return False

    def try_refresh_token(self, force=False):
        if not self.refresh:
            return
        if not force and self.expiry > float(time.time()):
            return

        try:
            with GlobalLock(self.__class__.__name__, True, self.token):
                url = f"{self.oauth_url}token"
                response = self.session.post(
                    url,
                    data={
                        "grant_type": "http://oauth.net/grant_type/device/1.0",
                        "code": self.refresh,
                        "client_secret": self.client_secret,
                        "client_id": self.client_id,
                    },
                )
                if not self._is_response_ok(response):
                    response = response.json()
                    g.notification(g.ADDON_NAME, "Failed to refresh RD token, please manually re-auth")
                    g.log(f"RD Refresh error: {response['error']}")
                    g.log(f"Invalid response from Real Debrid - {response}", "error")
                    return False
                response = response.json()
                self._save_settings(response)
                g.log("Real Debrid Token Refreshed")
                return True
        except RanOnceAlready:
            self._load_settings()
            return

    def _get_headers(self):
        # RD API uses form-encoded POST bodies (data=, not json=).
        # Do NOT set Content-Type here — requests auto-sets
        # application/x-www-form-urlencoded when data= is used.
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def post_url(self, url, post_data, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            return None

        response = self.session.post(url, data=post_data, headers=self._get_headers(), timeout=10)
        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.post_url(original_url, post_data, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def get_url(self, url, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            g.log("No Real Debrid Token Found")
            return None

        response = self.session.get(url, headers=self._get_headers(), timeout=10)

        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.get_url(original_url, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response

    def delete_url(self, url, fail_check=False):
        original_url = url
        url = self.base_url + url
        if not self.token:
            g.log("No Real Debrid Token Found")
            return None

        response = self.session.delete(url, headers=self._get_headers(), timeout=10)

        if not self._is_response_ok(response) and not fail_check:
            self.try_refresh_token(True)
            response = self.delete_url(original_url, fail_check=True)
        try:
            return response.json()
        except (ValueError, AttributeError):
            return response
        
    def check_hash(self, hash_value):
        magnet = f'magnet:?xt=urn:btih:{hash_value}'
        response = self.add_magnet(magnet)

        if not response or 'id' not in response:
            return {}

        torrent_id = response['id']
        self.torrent_select_all(torrent_id)
        torrent_info = self.torrent_info(torrent_id)

        if "files" in torrent_info:
            torrent_info["files"] = [file for file in torrent_info["files"] if 'sample' not in file['path'].lower() and source_utils.is_file_ext_valid(file["path"])]

        if torrent_info.get('status') == 'downloaded':
            hash_dict = {
                hash_value: {"torrent_id": torrent_id, "torrent_info": torrent_info, 'rd': [
                    {str(file['id']): {'filename': file['path'], 'filesize': file['bytes']}}
                    for file in torrent_info.get('files', []) if file.get('selected') == 1
                ]}
            }

            # NOTE: Do NOT delete torrent here — the resolver still needs valid
            # links from torrent_info to call resolve_hoster/unrestrict.
            # Cleanup (autodelete / smartdelete) is handled by the resolver's
            # _do_post_processing after the stream link has been obtained.
        else:
            self.delete_torrent(torrent_id)
            hash_dict = {}

        return hash_dict

    def _get_url_no_refresh(self, url):
        """
        GET request that bypasses the automatic token-refresh cycle.

        Used for deprecated / rate-limited endpoints (e.g. instantAvailability)
        where a non-200 response does NOT indicate an expired token.  Calling
        the normal get_url() on such endpoints causes try_refresh_token(True)
        to fire on every failed chunk, which:
          - blocks the scraping thread while the refresh POST runs,
          - fires a "Failed to refresh RD token" notification popup, and
          - can itself trigger a 429 on the token endpoint.

        Returns:
          - Parsed JSON dict on success
          - {'_rd_status': <int>} sentinel for 403 / 429 (no retry)
          - None for any other failure
        """
        full_url = self.base_url + url
        if not self.token:
            return None
        try:
            response = self.session.get(full_url, headers=self._get_headers(), timeout=10)
            if response.status_code in (403, 429):
                return {'_rd_status': response.status_code}
            if not response.ok:
                g.log(f"RD instantAvailability HTTP {response.status_code}", "warning")
                return None
            return response.json()
        except Exception as e:
            g.log(f"RD instantAvailability request error: {e}", "warning")
            return None

    def check_cache_batch(self, hash_list):
        """
        Batch cache check using /torrents/instantAvailability endpoint.

        Sends hashes in chunks of 50 and returns the set of hashes confirmed
        cached.  Uses _get_url_no_refresh() to prevent the token-refresh loop
        from firing on 403/429 responses (the endpoint is deprecated and will
        often return these codes regardless of token validity).

        On 403 or 429 the loop breaks immediately — no further chunks are sent
        and an empty set is returned. The caller returns 0 cached sources
        (no store-all fallback).

        :param hash_list: List of info_hash strings to check
        :type hash_list: list
        :return: Set of cached hash strings (lowercased)
        :rtype: set
        """
        cached_hashes = set()
        chunk_size = 50  # reduced from 100; smaller chunks are less likely to hit URL-length limits

        for i in range(0, len(hash_list), chunk_size):
            chunk = hash_list[i:i + chunk_size]
            hash_string = '/' + '/'.join(chunk)
            try:
                response = self._get_url_no_refresh(f"torrents/instantAvailability{hash_string}")

                if response is None:
                    continue

                # 403 = endpoint deprecated/forbidden for this account
                # 429 = rate limited — stop sending chunks immediately
                if isinstance(response, dict) and '_rd_status' in response:
                    status = response['_rd_status']
                    g.log(
                        f"RD instantAvailability: HTTP {status} — "
                        f"{'endpoint forbidden/deprecated' if status == 403 else 'rate limited'}. "
                        f"Stopping chunk loop.",
                        "warning",
                    )
                    break

                if not isinstance(response, dict):
                    continue

                for h, info in response.items():
                    # A hash is cached if it has a non-empty 'rd' list
                    if isinstance(info, dict) and info.get('rd'):
                        cached_hashes.add(h.lower())

            except Exception as e:
                g.log(f"RD instantAvailability chunk error: {e}", "warning")
                continue

            # Small inter-chunk delay to avoid consecutive rapid-fire requests
            if i + chunk_size < len(hash_list):
                time.sleep(0.2)

        return cached_hashes

    def torrent_select_all(self, torrent_id):
        try:
            torrent_info = self.torrent_info(torrent_id)
            files = torrent_info.get('files', [])
            
            valid_file_ids = [
                str(file['id']) for file in files
                if 'sample' not in file['path'].lower() 
                and source_utils.is_file_ext_valid(file['path'])
            ]

            if valid_file_ids:
                file_string = ','.join(valid_file_ids)
                return self.torrent_select(torrent_id, file_string)
            
            g.log(f"No valid video files found in torrent {torrent_id}", "warning")
            return None

        except Exception as e:
            g.log(f"Error selecting files for torrent {torrent_id}: {e}", "error")
            return None

    def add_magnet(self, magnet):
        post_data = {"magnet": magnet}
        url = "torrents/addMagnet"
        return self.post_url(url, post_data)

    def list_torrents(self):
        url = "torrents"
        return self.get_url(url)

    def torrent_info(self, id):
        url = f"torrents/info/{id}"
        return self.get_url(url)

    def torrent_select(self, torrent_id, file_id):
        url = f"torrents/selectFiles/{torrent_id}"
        post_data = {"files": file_id}
        return self.post_url(url, post_data)

    def resolve_hoster(self, link):
        from resources.lib.debrid.debrid_utils import get_user_ip
        from resources.lib.modules.exceptions import InfringingFile

        url = "unrestrict/link"
        post_data = {"link": link}
        user_ip = get_user_ip()
        if user_ip:
            post_data["ip"] = user_ip
        response = self.post_url(url, post_data)
        if isinstance(response, dict) and str(response.get('error_code')) == '35':
            g.log(
                f"RD unrestrict/link: infringing_file (error_code=35) — "
                f"link: {link[:80]}",
                "warning",
            )
            raise InfringingFile(link)
        try:
            return response["download"]
        except KeyError as e:
            raise UnexpectedResponse(response) from e

    def delete_torrent(self, id):
        url = f"torrents/delete/{id}"
        self.delete_url(url)

    def delete_download(self, id):
        """Delete a download item from user's download history."""
        url = f"downloads/delete/{id}"
        self.delete_url(url)

    def list_downloads(self):
        """List recent downloads (hoster unrestricted links) from user's account."""
        url = "downloads"
        return self.get_url(url) or []

    @staticmethod
    def is_streamable_storage_type(storage_variant):
        """
        Confirms that all files within the storage variant are video files
        This ensure the pack from RD is instantly streamable and does not require a download
        :param storage_variant:
        :return: BOOL
        """
        return len([i for i in storage_variant.values() if not source_utils.is_file_ext_valid(i["filename"])]) <= 0

    @use_cache(1)
    def get_relevant_hosters(self):
        host_list = self.get_url("hosts/status")
        if not host_list or "error" in host_list:
            return []
        return [domain for domain, status in host_list.items() if status["supported"] == 1 and status["status"] == "up"]

    def get_hosters(self, hosters):
        host_list = self.get_relevant_hosters()
        if host_list is None:
            host_list = self.get_relevant_hosters()
        if host_list is not None:
            hosters["premium"]["real_debrid"] = [(i, i.split(".")[0]) for i in host_list]
        else:
            hosters["premium"]["real_debrid"] = []

    @staticmethod
    def is_service_enabled():
        return g.get_bool_setting("realdebrid.enabled") and g.get_setting(RD_AUTH_KEY) is not None

    def get_account_status(self):
        status = None
        status_response = self.get_url("user")
        if isinstance(status_response, dict):
            status = status_response.get("type")
        return status or "unknown"

    def revoke_auth(self):
        """Remove Real-Debrid authorization after user confirmation."""
        if not self.token:
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Real-Debrid is not currently authorized.")
            return
        if not xbmcgui.Dialog().yesno(
            g.ADDON_NAME, "Remove Real-Debrid authorization?"
        ):
            return
        for key in (RD_AUTH_KEY, RD_REFRESH_KEY, RD_EXPIRY_KEY,
                    RD_SECRET_KEY, RD_CLIENT_ID_KEY, RD_USERNAME_KEY, RD_STATUS_KEY):
            g.set_setting(key, "")
        self.token = ""
        xbmcgui.Dialog().ok(g.ADDON_NAME, "Real-Debrid authorization removed.")

    def account_info_to_dialog(self):
        """
        Fetch account info from Real-Debrid API and display in a select dialog.
        Mirrors Account Manager's RealDebrid.account_info_to_dialog() format.
        """
        from datetime import datetime
        try:
            user_info = self.get_url("user")
            if not isinstance(user_info, dict) or "username" not in user_info:
                xbmcgui.Dialog().ok(g.ADDON_NAME, "Real-Debrid: Could not retrieve account information.")
                return
            try:
                expires = datetime.strptime(user_info["expiration"], "%Y-%m-%dT%H:%M:%S.%fZ")
                days_remaining = (expires - datetime.today()).days
                expires_str = expires.strftime("%A, %B %d, %Y")
            except Exception:
                days_remaining = "N/A"
                expires_str = user_info.get("expiration", "N/A")
            lines = [
                "Username:  %s" % user_info.get("username", "N/A"),
                "Email:     %s" % user_info.get("email", "N/A"),
                "Status:    %s" % user_info.get("type", "N/A").capitalize(),
                "Expires:   %s" % expires_str,
                "Days left: %s" % days_remaining,
                "Points:    %s" % user_info.get("points", "N/A"),
            ]
            xbmcgui.Dialog().select("%s: Real-Debrid Account" % g.ADDON_NAME, lines)
        except Exception as e:
            g.log("RD account_info_to_dialog error: %s" % e, "error")
            xbmcgui.Dialog().ok(g.ADDON_NAME, "Real-Debrid: Could not retrieve account information.")

