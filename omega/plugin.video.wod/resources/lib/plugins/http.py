from ..plugin import Plugin
from ..DI import DI
import xml.etree.ElementTree as ET


class http(Plugin):
    name = "http"

    def get_list(self, url):
        if url.startswith("http"):
            return DI.session.get(url).text
