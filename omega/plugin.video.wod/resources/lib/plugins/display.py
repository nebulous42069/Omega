from ..plugin import Plugin
from xbmcplugin import addDirectoryItems, endOfDirectory, setContent
from ..DI import DI
import sys

route_plugin = DI.plugin


class display(Plugin):
    name = "display"

    def display_list(self, jen_list):
        display_list = [(route_plugin.url_for_path(item["link"]), item["list_item"], item["is_dir"]) for item in jen_list]    	
        addDirectoryItems(route_plugin.handle, display_list, len(display_list))
        setContent(int(sys.argv[1]), 'videos') 
        endOfDirectory(route_plugin.handle)
        return True
