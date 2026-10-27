"""Song-relative clock for streams whose player time may be station-relative."""
import threading
import time


class StreamClock:
    def __init__(self, now=time.monotonic):
        self._now = now
        self._lock = threading.Lock()
        self.reset()

    def reset(self, player_time=None):
        with self._lock:
            self.elapsed = 0.0
            self.last_wall = self._now()
            self.last_player = player_time
            self.player_clock = False
            self.was_blocked = False

    def sample(self, player_time=None, blocked=False):
        with self._lock:
            now = self._now()
            wall_delta = max(0.0, now - self.last_wall)
            delta = None
            if player_time is not None and self.last_player is not None:
                delta = player_time - self.last_player
                if delta > 0:
                    self.player_clock = True
            if not blocked and not self.was_blocked:
                if delta is not None and self.player_clock:
                    # A station clock may restart at a track boundary or reconnect.
                    # Rebase without importing its absolute value into this song.
                    self.elapsed += max(0.0, delta)
                elif not self.player_clock:
                    self.elapsed += wall_delta
                # Once a usable player clock is established, a stalled/missing
                # sample freezes lyrics rather than running ahead of the audio.
            self.last_wall = now
            self.last_player = player_time
            self.was_blocked = blocked
            return self.elapsed
