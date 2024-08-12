from ..plugin import Plugin
import json
import xbmc

class json_parser(Plugin):
    name = "json_parser"
    description = "add json format support"
    priority = 0

    def parse_list(self, url: str, response):
        if url.endswith(".json") or '"items": [' in response :
            try:
                return json.loads(response)["items"]
            except json.decoder.JSONDecodeError:
                xbmc.log(f"invalid json: {response}", xbmc.LOGINFO)
