from resources.lib.gui.windows.smartplay_window import SmartPlayWindow
from resources.lib.modules.globals import g


class PlayingNext(SmartPlayWindow):
    """
    Dialog to provide quick skipping to next playlist item if available.
    Includes anime Skip Outro button when outro timestamp data is available.
    """

    def __init__(self, xml_file, xml_location, item_information=None):
        super().__init__(xml_file, xml_location, item_information=item_information)
        self.default_action = g.get_int_setting("playingnext.defaultaction")

        # Check for anime outro skip data and set window property for skin visibility
        self._skip_outro_end = None
        outro_end = g.get_runtime_setting("anime.skipOutroEnd")
        if outro_end:
            try:
                self._skip_outro_end = int(float(outro_end))
                self.setProperty("anime.skipOutroEnd", str(self._skip_outro_end))
            except (ValueError, TypeError):
                pass
            g.clear_runtime_setting("anime.skipOutroEnd")

    def smart_play_action(self):
        if self.default_action == 1 and self.playing_file == self.getPlayingFile() and not self.closed:
            self.pause()

    def handle_action(self, action, control_id=None):
        if action == 7:
            if control_id == 3004 and self._skip_outro_end:
                # Skip Outro — seek past credits but stay on current episode
                self.seekTime(self._skip_outro_end)
                self.close()
                return
        # Fall through to parent for Play Now (3001), Close (3002), Cancel (3003)
        super().handle_action(action, control_id)
