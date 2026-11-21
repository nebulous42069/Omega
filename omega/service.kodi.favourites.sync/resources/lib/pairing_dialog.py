"""Google Drive pairing UI with offline QR as the default.

Kodi cannot embed a QR image inside skin-native DialogProgress, so QR mode uses
an add-on-owned WindowXMLDialog. The native progress window remains optional.
"""

import os
import textwrap
import struct
import zlib
import traceback

from resources.lib.kodi_compat import (
    addon_path, get_setting_bool, log, profile_dir, progress_dialog, xbmcgui,
)


def _pairing_style(addon):
    """QR is the default even for upgrades from versions with a saved enum=0.

    Previous versions used an enum whose persisted zero overrode the new QR
    default. This NEW, explicit opt-out setting is false unless a user
    deliberately asks to display the text-only dialog.
    """
    return 0 if get_setting_bool(addon, "text_only_pairing", False) else 1


def _png_chunk(tag, payload):
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xffffffff)


def _render_qr_png(verification_uri):
    """Create a scannable monochrome QR PNG from the complete pairing URL.

    No network access, PIL, or add-on installation is required. Padding is
    supplied by the QR encoder's four-module quiet zone.
    """
    # Kodi provides a Python-3.8-compatible QR encoder through its official
    # script.module.qrcode dependency (declared in addon.xml). Do not import
    # the previously bundled QRCode 8.x package: its evaluated PEP 585 types
    # raise TypeError on Kodi builds running Python 3.8.
    # QRCode.get_matrix() does NOT use PIL, so no Pillow dependency is needed.
    from qrcode.main import QRCode
    from qrcode.constants import ERROR_CORRECT_M
    qr = QRCode(error_correction=ERROR_CORRECT_M, border=4, box_size=1)
    qr.add_data(verification_uri, optimize=0)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    side = len(matrix)
    if not side or side > 180:
        raise ValueError("QR code exceeds the supported screen size")
    scale = max(2, min(10, 380 // side))
    width = side * scale
    # PNG greyscale, filter 0, 8-bit luminance. Black modules are 0.
    rows = bytearray()
    for line in matrix:
        row = b"\x00" + bytes((0 if cell else 255) for cell in line for _ in range(scale))
        for _ in range(scale):
            rows.extend(row)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, width, 8, 0, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(rows), level=7)))
    png.extend(_png_chunk(b"IEND", b""))
    return bytes(png)


def _generate_qr_image(addon, verification_uri):
    """Atomically write pairing QR in add-on user data, not the source folder."""
    target_path = os.path.join(profile_dir(addon), "pairing-qr.png")
    temporary_path = target_path + ".tmp"
    image = _render_qr_png(verification_uri)
    try:
        with open(temporary_path, "wb") as handle:
            handle.write(image)
        os.replace(temporary_path, target_path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
    return target_path


def _download_qr_image(addon, verification_uri):
    """Legacy entry point retained; despite the name, no download occurs."""
    return _generate_qr_image(addon, verification_uri)


def _remaining_label(line3):
    """Extract readable countdown without hiding the complete pairing URL."""
    if " | " in line3:
        return line3.rsplit(" | ", 1)[-1]
    return ""


class QRPairingDialog:
    """Backwards-compatible pairing UI wrapper for the pairing flow."""

    def __init__(self, addon, heading, verification_uri, user_code):
        self._dialog = None
        self._custom = False
        self._qr_image_path = None
        self.heading = heading
        self.verification_uri = verification_uri
        self.user_code = user_code
        self._qr_error = ""

        # 0: skin-native without QR, 1: QR by default.
        selected_style = _pairing_style(addon)
        log("Pairing window preference: %s" % ("QR" if selected_style == 1 else "skin-native"), addon=addon)
        qr_failure = None
        if selected_style == 1 and xbmcgui is not None:
            # QR image creation is independent of the window. A custom XML
            # load failure should not send TV users back to typing a URL.
            try:
                self._qr_image_path = _generate_qr_image(addon, verification_uri)
            except Exception as exc:
                qr_failure = "QR image generation failed: %s: %s" % (type(exc).__name__, exc)
                log(qr_failure + "\n" + traceback.format_exc(), level="error", addon=addon)
            if self._qr_image_path:
                try:
                    self._dialog = _KodiQRPairingDialog(
                        "pairing-dialog.xml", addon_path(addon), "default", "1080i",
                        heading=heading,
                        verification_uri=verification_uri,
                        user_code=user_code,
                        qr_image_path=self._qr_image_path,
                    )
                    self._dialog.show()
                    self._custom = True
                    log("QR pairing XML window shown", addon=addon)
                except Exception as exc:
                    qr_failure = "QR XML window failed: %s: %s" % (type(exc).__name__, exc)
                    log(qr_failure + "\n" + traceback.format_exc(), level="error", addon=addon)
                    if self._dialog is not None:
                        try:
                            self._dialog.close()
                        except Exception:
                            pass
                    self._dialog = None
                # XML isn't always loaded by the chosen skin. If it fails,
                # construct a standalone QR window without any skin XML.
                if self._dialog is None and _KodiProgrammaticQRDialog is not None:
                    try:
                        self._dialog = _KodiProgrammaticQRDialog(
                            addon=addon, heading=heading,
                            verification_uri=verification_uri,
                            user_code=user_code,
                            qr_image_path=self._qr_image_path,
                        )
                        self._dialog.show()
                        self._custom = True
                        qr_failure = None
                        log("QR pairing fallback window shown (no skin XML)", addon=addon)
                    except Exception as exc:
                        qr_failure = "Standalone QR window failed: %s: %s" % (type(exc).__name__, exc)
                        log(qr_failure + "\n" + traceback.format_exc(), level="error", addon=addon)
                        if self._dialog is not None:
                            try:
                                self._dialog.close()
                            except Exception:
                                pass
                        self._dialog = None
            if self._dialog is None:
                self._remove_qr_file()

        if self._dialog is None:
            # Kodi's own DialogProgress uses the ACTIVE skin's font, size,
            # positioning, colours and built-in Cancel button.
            message = self._native_message()
            if qr_failure:
                self._qr_error = qr_failure
                # No more silent "why is the QR missing?" failure. The
                # detailed exception is in kodi.log for diagnostics.
                message = "QR unavailable (%s).\n%s" % (qr_failure, message)
            self._dialog = progress_dialog(heading, message)

    def _native_message(self, remaining=""):
        # Keep the COMPLETE URL, including the ?code=... parameter. Some
        # authorization bridges do not have a separate manual-code form.
        # Avoid duplicating the long link in status messages.
        message = "Open this link on your phone:\n%s" % self.verification_uri
        if self.user_code:
            message += "\nPairing code: %s" % self.user_code
        if remaining:
            message += " (%s)" % remaining
        return message

    def update(self, percent, line1="", line2="", line3=""):
        if self._dialog is None:
            return
        if self._custom:
            self._dialog.update_status(percent, line1, line2, line3)
            return
        message = self._native_message(_remaining_label(line3))
        if self._qr_error:
            message = "QR unavailable (%s).\n%s" % (self._qr_error, message)
        # Kodi 19+ DialogProgress.update takes ONE message argument (line2 and
        # line3 were removed). Keep the standalone fallback compatible too.
        self._dialog.update(int(max(0, min(100, percent))), message)

    def iscanceled(self):
        if self._dialog is None:
            return False
        if self._custom:
            return bool(getattr(self._dialog, "canceled", False))
        return bool(self._dialog.iscanceled())

    def _remove_qr_file(self):
        if self._qr_image_path:
            try:
                os.remove(self._qr_image_path)
            except OSError:
                pass
            self._qr_image_path = None

    def close(self):
        if self._dialog is not None:
            try:
                self._dialog.close()
            finally:
                self._remove_qr_file()
        else:
            self._remove_qr_file()


if xbmcgui is not None:
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
            self._initialized = False
            self._pending = {
                "percent": 0,
                "line1": "Scan QR code to authorize Google Drive.",
                "line3": "",
            }
            super().__init__(*args, **kwargs)

        def onInit(self):
            self._set_label(self._HEADING, self.heading)
            self.getControl(self._QR_IMAGE).setImage(self.qr_image_path, False)
            self._initialized = True
            self._render_status()

        def update_status(self, percent, line1="", line2="", line3=""):
            self._pending = {"percent": percent, "line1": line1, "line3": line3}
            if self._initialized:
                self._render_status()

        def _render_status(self):
            pct = int(max(0, min(100, self._pending.get("percent", 0))))
            self._set_label(self._STATUS, "[B]%s%%[/B]\n%s" % (pct, self._pending.get("line1", "")))
            # The URL, pairing code and Cancel button now have entirely
            # separate controls, so text wrapping cannot collide with Cancel.
            wrapped = "\n".join(textwrap.wrap(self.verification_uri, width=43,
                                               break_long_words=True,
                                               break_on_hyphens=False))
            self._set_label(self._URL, "URL:\n%s" % wrapped)
            # The complete URL and QR already contain the pairing code.
            # Only display the countdown here to avoid repeating the code.
            countdown = _remaining_label(self._pending.get("line3", ""))
            self._set_label(self._CODE, countdown)

        def _set_label(self, control_id, value):
            control = self.getControl(control_id)
            if hasattr(control, "setText"):
                control.setText(value)
            else:
                control.setLabel(value)

        def onAction(self, action):
            if action.getId() in self._CANCEL_ACTIONS:
                self.canceled = True
                self.close()

        def onClick(self, controlId):
            if controlId == self._CANCEL:
                self.canceled = True
                self.close()
else:
    _KodiQRPairingDialog = None



if xbmcgui is not None and hasattr(xbmcgui, "WindowDialog"):
    class _KodiProgrammaticQRDialog(xbmcgui.WindowDialog):
        """QR window with Kodi's GUI controls, without any custom skin XML.

        All coordinates are 1280x720 Kodi virtual screen coordinates. Kodi
        scales these controls for the running skin and actual display.
        """
        _CANCEL_ACTIONS = {9, 10, 92, 216, 247, 257, 275, 61467}

        def __init__(self, addon, heading, verification_uri, user_code, qr_image_path):
            super().__init__()
            self.canceled = False
            self._initialized = False
            self.verification_uri = verification_uri
            self.user_code = user_code
            self._pending = {"percent": 0, "line1": "Scan QR code to authorize Google Drive.", "line3": ""}
            asset_dir = os.path.join(addon_path(addon), "resources", "skins", "default", "media")
            bg = os.path.join(asset_dir, "qr-dialog-background.png")
            header = os.path.join(asset_dir, "qr-dialog-header.png")
            self._background = xbmcgui.ControlImage(0, 0, 1280, 720, bg)
            self._card = xbmcgui.ControlImage(145, 65, 990, 590, bg)
            self._header = xbmcgui.ControlImage(145, 65, 990, 65, header)
            self._title = xbmcgui.ControlLabel(175, 78, 920, 42, heading, font="font13", textColor="0xFFFFFFFF")
            self._qr = xbmcgui.ControlImage(185, 175, 360, 360, qr_image_path, aspectRatio=2)
            self._instructions = xbmcgui.ControlTextBox(575, 175, 510, 115, font="font13", textColor="0xFFFFFFFF")
            self._url = xbmcgui.ControlTextBox(575, 290, 510, 150, font="font13", textColor="0xFFFFFFFF")
            self._code = xbmcgui.ControlLabel(575, 450, 510, 45, "", font="font13", textColor="0xFFFFFFFF")
            self._cancel = xbmcgui.ControlButton(
                852, 554, 225, 58, "Cancel", focusTexture=header,
                noFocusTexture=bg, font="font13", textColor="0xFFFFFFFF",
                focusedColor="0xFFFFFFFF", alignment=2,
            )
            self.addControls([
                self._background, self._card, self._header, self._title,
                self._qr, self._instructions, self._url, self._code, self._cancel,
            ])
            self._initialized = True
            self._render_status()

        def onInit(self):
            try:
                self.setFocus(self._cancel)
            except Exception:
                pass

        def update_status(self, percent, line1="", line2="", line3=""):
            self._pending = {"percent": percent, "line1": line1, "line3": line3}
            if self._initialized:
                self._render_status()

        def _render_status(self):
            self._instructions.setText(self._pending.get("line1", "Scan QR code to authorize Google Drive."))
            wrapped = "\n".join(textwrap.wrap(
                self.verification_uri, width=40, break_long_words=True,
                break_on_hyphens=False))
            self._url.setText("URL:\n" + wrapped)
            countdown = _remaining_label(self._pending.get("line3", ""))
            self._code.setLabel(countdown)

        def onAction(self, action):
            if action.getId() in self._CANCEL_ACTIONS:
                self.canceled = True
                self.close()

        def onClick(self, controlId):
            if controlId == self._cancel.getId():
                self.canceled = True
                self.close()
else:
    _KodiProgrammaticQRDialog = None

def create_pairing_dialog(addon, heading, verification_uri, user_code):
    return QRPairingDialog(addon, heading, verification_uri, user_code)
