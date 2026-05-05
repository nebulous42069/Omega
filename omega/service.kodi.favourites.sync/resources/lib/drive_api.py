import json
import mimetypes
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TOKEN_URI = "https://oauth2.googleapis.com/token"
DEVICE_AUTH_URI = "https://oauth2.googleapis.com/device/code"
DRIVE_FILES_API = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_OPENID_CONFIG = "https://accounts.google.com/.well-known/openid-configuration"
ISO8601_Z = "%Y-%m-%dT%H:%M:%S.%fZ"
APPDATA_SCOPE = "https://www.googleapis.com/auth/drive.appdata"
DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DEFAULT_SCOPES = [APPDATA_SCOPE, DRIVE_FILE_SCOPE]
APPDATA_FOLDER = "appDataFolder"


class DriveError(Exception):
    pass


def _request_json(url, method="GET", headers=None, body=None):
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise DriveError(_format_http_error(exc))
    except URLError as exc:
        raise DriveError("Network error: %s" % exc)


def _request_bytes(url, method="GET", headers=None, body=None):
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as exc:
        raise DriveError(_format_http_error(exc))
    except URLError as exc:
        raise DriveError("Network error: %s" % exc)


def _format_http_error(exc):
    try:
        body = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:  # pragma: no cover
        body = ""
    if body:
        return "HTTP %s %s: %s" % (exc.code, exc.reason, body)
    return "HTTP %s %s" % (exc.code, exc.reason)


def parse_google_timestamp(value):
    if not value:
        return None
    if value.endswith("Z"):
        trimmed = value.replace("Z", "+00:00")
        return datetime.fromisoformat(trimmed)
    return datetime.fromisoformat(value)


def normalize_metadata(data):
    if not data:
        return None
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "modified_time": parse_google_timestamp(data.get("modifiedTime")),
        "modified_time_raw": data.get("modifiedTime"),
        "version": data.get("version"),
        "size": int(data["size"]) if data.get("size") not in (None, "") else None,
    }


class OAuthTokenProvider:
    def __init__(
        self,
        client_id,
        client_secret,
        refresh_token,
        refresh_secret="",
        scopes=None,
        access_token="",
        access_token_expiry=None,
        refresh_bridge_url="",
    ):
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.refresh_token = refresh_token or ""
        self.refresh_secret = refresh_secret or ""
        self.scopes = list(scopes or DEFAULT_SCOPES)
        self._access_token = access_token or None
        self._access_token_expiry = access_token_expiry
        self.refresh_bridge_url = (refresh_bridge_url or "").rstrip("/")

    def validate(self):
        missing = []
        if not self._access_token and not self.refresh_bridge_url and not self.client_id:
            missing.append("oauth_client_id")
        if not self._access_token and not self.refresh_token:
            missing.append("oauth_refresh_token")
        if missing:
            raise DriveError("OAuth configuration is missing: %s" % ", ".join(missing))

    def auth_header(self):
        self.validate()
        if self._token_is_fresh():
            return {"Authorization": "Bearer %s" % self._access_token}

        response = self._refresh_token()
        access_token = response.get("access_token")
        if not access_token:
            raise DriveError("Google token response did not include an access token")
        expires_in = int(response.get("expires_in", 3600))
        self._access_token = access_token
        self._access_token_expiry = datetime.now(timezone.utc) + timedelta(seconds=max(60, expires_in - 60))
        return {"Authorization": "Bearer %s" % self._access_token}

    def _token_is_fresh(self):
        return (
            self._access_token is not None
            and self._access_token_expiry is not None
            and datetime.now(timezone.utc) < self._access_token_expiry
        )

    def _refresh_token(self):
        if self.refresh_bridge_url:
            return _request_json(
                "%s/api/google/refresh" % self.refresh_bridge_url,
                method="POST",
                headers={"Content-Type": "application/json"},
                body=json.dumps(
                    {
                        "refresh_token": self.refresh_token,
                        "refresh_secret": self.refresh_secret,
                    }
                ).encode("utf-8"),
            )

        body = {
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        if self.client_secret:
            body["client_secret"] = self.client_secret

        return _request_json(
            TOKEN_URI,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=urlencode(body).encode("utf-8"),
        )


class DriveClient:
    def __init__(self, token_provider):
        self.token_provider = token_provider

    def _auth_header(self):
        return self.token_provider.auth_header()

    def get_file(self, file_id):
        params = urlencode(
            {
                "fields": "id,name,modifiedTime,version,size",
                "supportsAllDrives": "true",
            }
        )
        url = "%s/%s?%s" % (DRIVE_FILES_API, quote(file_id), params)
        data = _request_json(url, headers=self._auth_header())
        return normalize_metadata(data)

    def find_file_by_name(self, folder_id, filename, remote_mode="appdata"):
        if remote_mode == "appdata":
            return self.find_appdata_file(filename)

        query = [
            "name='%s'" % filename.replace("'", "\\'"),
            "trashed=false",
        ]
        if folder_id:
            query.append("'%s' in parents" % folder_id)
        params = urlencode(
            {
                "q": " and ".join(query),
                "pageSize": 1,
                "fields": "files(id,name,modifiedTime,version,size)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
        )
        data = _request_json("%s?%s" % (DRIVE_FILES_API, params), headers=self._auth_header())
        files = data.get("files") or []
        return normalize_metadata(files[0]) if files else None

    def find_appdata_file(self, filename):
        params = urlencode(
            {
                "q": "name='%s' and trashed=false and '%s' in parents"
                % (filename.replace("'", "\\'"), APPDATA_FOLDER),
                "pageSize": 1,
                "fields": "files(id,name,modifiedTime,version,size)",
                "spaces": APPDATA_FOLDER,
            }
        )
        data = _request_json("%s?%s" % (DRIVE_FILES_API, params), headers=self._auth_header())
        files = data.get("files") or []
        return normalize_metadata(files[0]) if files else None

    def resolve_remote(self, file_id, folder_id, filename, remote_mode="appdata"):
        if remote_mode == "file_id" and file_id:
            return self.get_file(file_id)
        if not filename:
            raise DriveError("Remote filename is required when Drive file ID is empty")
        return self.find_file_by_name(folder_id, filename, remote_mode=remote_mode)

    def download_file(self, file_id):
        url = "%s/%s?alt=media" % (DRIVE_FILES_API, quote(file_id))
        return _request_bytes(url, headers=self._auth_header())

    def create_file(self, folder_id, filename, content, remote_mode="appdata"):
        metadata = {"name": filename}
        if remote_mode == "appdata":
            metadata["parents"] = [APPDATA_FOLDER]
        elif folder_id:
            metadata["parents"] = [folder_id]
        return self._multipart_upload(metadata, content)

    def update_file(self, file_id, filename, content):
        metadata = {"name": filename}
        return self._multipart_upload(metadata, content, file_id=file_id)

    def _multipart_upload(self, metadata, content, file_id=None):
        boundary = "kodi-favourites-sync-boundary"
        guessed_type = mimetypes.guess_type(metadata.get("name", ""))[0] or "application/octet-stream"
        body = (
            ("--%s\r\n" % boundary).encode("utf-8")
            + b"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            + json.dumps(metadata, separators=(",", ":")).encode("utf-8")
            + b"\r\n"
            + ("--%s\r\n" % boundary).encode("utf-8")
            + ("Content-Type: %s\r\n\r\n" % guessed_type).encode("utf-8")
            + content
            + b"\r\n"
            + ("--%s--\r\n" % boundary).encode("utf-8")
        )

        if file_id:
            url = "%s/%s?uploadType=multipart&fields=id,name,modifiedTime,version,size" % (
                DRIVE_UPLOAD_API,
                quote(file_id),
            )
            method = "PATCH"
        else:
            url = "%s?uploadType=multipart&fields=id,name,modifiedTime,version,size" % DRIVE_UPLOAD_API
            method = "POST"

        headers = self._auth_header()
        headers["Content-Type"] = "multipart/related; boundary=%s" % boundary
        data = _request_json(url, method=method, headers=headers, body=body)
        return normalize_metadata(data)


def start_device_authorization(client_id, scopes=None):
    requested_scopes = scopes or DEFAULT_SCOPES
    body = urlencode(
        {
            "client_id": client_id,
            "scope": " ".join(requested_scopes),
        }
    ).encode("utf-8")
    return _request_json(
        DEVICE_AUTH_URI,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
    )


def exchange_device_code(client_id, client_secret, device_code):
    body = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }
    if client_secret:
        body["client_secret"] = client_secret
    return _request_json(
        TOKEN_URI,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=urlencode(body).encode("utf-8"),
    )
