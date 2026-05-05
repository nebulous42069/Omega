import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from resources.lib.drive_api import DriveError


def _request_json(url, method="GET", headers=None, body=None, timeout=30):
    request = Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body_text = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:  # pragma: no cover
            body_text = ""
        if body_text:
            raise DriveError("HTTP %s %s: %s" % (exc.code, exc.reason, body_text))
        raise DriveError("HTTP %s %s" % (exc.code, exc.reason))
    except URLError as exc:
        raise DriveError("Network error: %s" % exc)


class OAuthBridgeClient:
    def __init__(self, base_url):
        self.base_url = (base_url or "").rstrip("/")

    def validate(self):
        if not self.base_url:
            raise DriveError("OAuth bridge URL is not configured")

    def create_pairing(self):
        self.validate()
        return _request_json(
            "%s/api/pairings" % self.base_url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=b"{}",
        )

    def pairing_status(self, pairing_id, poll_token):
        self.validate()
        url = "%s/api/pairings/%s?poll_token=%s" % (
            self.base_url,
            quote(pairing_id),
            quote(poll_token),
        )
        return _request_json(url)

    def claim_pairing(self, pairing_id, poll_token):
        self.validate()
        url = "%s/api/pairings/%s/claim" % (self.base_url, quote(pairing_id))
        body = json.dumps({"poll_token": poll_token}).encode("utf-8")
        return _request_json(
            url,
            method="POST",
            headers={"Content-Type": "application/json"},
            body=body,
        )
