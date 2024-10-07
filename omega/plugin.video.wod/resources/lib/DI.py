import requests
import routing


class DI:
    session = requests.Session()

    @property
    def plugin(self):
        try:
            return routing.Plugin()
        except AttributeError:
            from routing.routing import Plugin

            return Plugin()


DI = DI()
