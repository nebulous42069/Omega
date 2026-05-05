import os
import textwrap
from urllib.parse import quote
from urllib.request import urlopen

from resources.lib.kodi_compat import addon_path, profile_dir, progress_dialog, xbmcgui


def _qr_image_url(url):
    return "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=%s" % quote(url, safe="")


def _download_qr_image(addon, verification_uri):
    target_path = os.path.join(profile_dir(addon), "pairing-qr.png")
    with urlopen(_qr_image_url(verification_uri), timeout=20) as response:
        with open(target_path, "wb") as handle:
            handle.write(response.read())
    return target_path


class QRPairingDialog:
    def __init__(self, addon, heading, verification_uri, user_code):
        self._dialog = None
        self.heading = heading
        self.verification_uri = verification_uri
        self.user_code = user_code
        if xbmcgui is not None:
            qr_image_path = _download_qr_image(addon, verification_uri)
            self._dialog = _KodiQRPairingDialog(
                "pairing-dialog.xml",
                addon_path(addon),
                "default",
                heading=heading,
                verification_uri=verification_uri,
                user_code=user_code,
                qr_image_path=qr_image_path,
            )
            self._dialog.show()
        else:
            self._dialog = progress_dialog(heading, "Open the pairing URL on another device.")

    def update(self, percent, line1="", line2="", line3=""):
        if self._dialog is None:
            return
        if xbmcgui is None:
            try:
                self._dialog.update(percent, line1, line2, line3)
            except TypeError:
                self._dialog.update(percent, "\n".join(part for part in (line1, line2, line3) if part))
            return
        self._dialog.update_status(percent, line1, line2, line3)

    def iscanceled(self):
        if xbmcgui is None:
            return self._dialog.iscanceled()
        return bool(getattr(self._dialog, "canceled", False))

    def close(self):
        if self._dialog is None:
            return
        if xbmcgui is None:
            self._dialog.close()
            return
        self._dialog.close()


class _KodiQRPairingDialog(xbmcgui.WindowXMLDialog):
    _HEADING = 1000
    _QR_IMAGE = 1001
    _STATUS = 1002
    _URL = 1003
    _CODE = 1004
    _CANCEL = 1005
    _CANCEL_ACTIONS = {9, 10, 92, 216, 247, 257, 275, 61467}

    def __init__(self, *args, **kwargs):
        self.heading = kwargs.pop("heading")
        self.verification_uri = kwargs.pop("verification_uri")
        self.user_code = kwargs.pop("user_code")
        self.qr_image_path = kwargs.pop("qr_image_path")
        self.canceled = False
        self._pending = {
            "percent": 0,
            "line1": "Scan the QR code with your phone.",
            "line2": "Open this link on your phone:",
            "line3": self.verification_uri,
        }
        super().__init__(*args, **kwargs)

    def onInit(self):
        self._set_label(self._HEADING, self.heading)
        self._set_image(self._QR_IMAGE, self.qr_image_path)
        self._render_status()

    def update_status(self, percent, line1="", line2="", line3=""):
        self._pending = {
            "percent": percent,
            "line1": line1,
            "line2": line2,
            "line3": line3,
        }
        self._render_status()

    def _render_status(self):
        wrapped_url = ""
        detail_lines = []
        for part in (self._pending.get("line1", ""), self._pending.get("line2", "")):
            if part:
                detail_lines.append(part)

        raw_line3 = self._pending.get("line3", "")
        if raw_line3.startswith("URL: "):
            wrapped_url = "\n".join(textwrap.wrap(raw_line3[5:], width=34))
        elif raw_line3:
            detail_lines.append(raw_line3)

        detail_lines.append("Code: %s" % (self.user_code or "-"))
        message = "[B]%s%%[/B]\n%s" % (
            int(max(0, min(100, self._pending.get("percent", 0)))),
            "\n".join(detail_lines),
        )
        if wrapped_url:
            message += "\nURL:\n%s" % wrapped_url
        self._set_label(self._STATUS, message)

    def _set_label(self, control_id, value):
        control = self.getControl(control_id)
        if control:
            if hasattr(control, "setText"):
                control.setText(value)
            else:
                control.setLabel(value)

    def _set_image(self, control_id, value):
        control = self.getControl(control_id)
        if control:
            control.setImage(value, False)

    def onAction(self, action):
        if action.getId() in self._CANCEL_ACTIONS:
            self.canceled = True
            self.close()

    def onClick(self, controlId):
        if controlId == self._CANCEL:
            self.canceled = True
            self.close()


def create_pairing_dialog(addon, heading, verification_uri, user_code):
    return QRPairingDialog(addon, heading, verification_uri, user_code)
