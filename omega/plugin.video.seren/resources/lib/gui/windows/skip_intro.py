"""Skip overlay dialog — renders one of four button types during playback.

Used for intro / recap / credits / preview segments. The button label is set
dynamically from the segment_type passed by the caller, so a single window XML
serves all four cases. Auto-closes when playback passes skip_end or the file
changes.
"""

import xbmc

from resources.lib.gui.windows.base_window import BaseWindow
from resources.lib.modules.globals import g

# String IDs for button labels — must match strings.po entries
_LABEL_BY_TYPE = {
    "intro": 30765,    # "Skip Intro"
    "recap": 30894,    # "Skip Recap"
    "credits": 30785,  # "Skip Outro" — re-used for credits (same English wording)
    "preview": 30895,  # "Skip Preview"
}

_BUTTON_SKIP = 3001
_BUTTON_CLOSE = 3002


class SkipIntro(BaseWindow):
    """Overlay dialog shown during a skip segment."""

    def __init__(self, xml_file, xml_location, item_information=None, skip_end=0, segment_type="intro"):
        super().__init__(xml_file, xml_location, item_information=item_information)
        self.player = xbmc.Player()
        self.skip_end = skip_end
        self.segment_type = segment_type if segment_type in _LABEL_BY_TYPE else "intro"
        self.closed = False
        try:
            self.playing_file = self.player.getPlayingFile()
        except RuntimeError:
            self.playing_file = None

    def __del__(self):
        self.player = None

    def onInit(self):
        super().onInit()
        # Apply the type-specific button label before showing.
        try:
            label_id = _LABEL_BY_TYPE.get(self.segment_type, 30765)
            label = g.get_language_string(label_id)
            ctrl = self.getControl(_BUTTON_SKIP)
            if ctrl and label:
                ctrl.setLabel(label)
        except Exception:
            # Non-fatal — fall through with whatever the XML default label is.
            g.log_stacktrace()

        self._background_monitor()

    def _background_monitor(self):
        """Monitor playback position; auto-close when segment ends or file changes."""
        try:
            while (
                not self.closed
                and not g.abort_requested()
                and self.player.isPlaying()
                and self.playing_file == self.player.getPlayingFile()
            ):
                current = int(self.player.getTime())
                if current > self.skip_end:
                    break
                xbmc.sleep(1000)
        except RuntimeError:
            pass
        self.close()

    def handle_action(self, action_id, control_id=None):
        if action_id == 7:
            if control_id == _BUTTON_SKIP:
                # Skip — seek to end of segment (already includes skip.offset)
                try:
                    self.player.seekTime(self.skip_end)
                except RuntimeError:
                    pass
                self.close()
            elif control_id == _BUTTON_CLOSE:
                # Close — dismiss without skipping
                self.close()

    def close(self):
        self.closed = True
        super().close()
