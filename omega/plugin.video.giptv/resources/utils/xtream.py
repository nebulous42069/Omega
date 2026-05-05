class _XtreamState:
    def __init__(self):
        self.server = ""
        self.username = ""
        self.password = ""

    def is_ready(self):
        return bool(self.server and self.username and self.password)


STATE = _XtreamState()
