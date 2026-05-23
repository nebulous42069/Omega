import xbmcgui

from resources.lib.gui.windows.source_window import SourceWindow
from resources.lib.modules.cacheAssist import CacheAssistHelper
from resources.lib.modules.exceptions import FailureAtRemoteParty
from resources.lib.modules.exceptions import GeneralCachingFailure
from resources.lib.modules.globals import g
from resources.lib.modules.source_sorter import SourceSorter


class ManualCacheWindow(SourceWindow):
    def __init__(self, xml_file, location, item_information=None, sources=None, close_text=None):
        super().__init__(xml_file, location, item_information=item_information, sources=sources)
        self.sources = SourceSorter(self.item_information).sort_sources(self.sources)
        self.cache_assist_helper = CacheAssistHelper()
        self.cached_source = None
        if not close_text:
            close_text = g.get_language_string(30459)
        self.setProperty("close.text", close_text)

    def _cache_item(self):
        uncached_source = self.sources[self.display_list.getSelectedPosition()]
        cache_assist_module = self.cache_assist_helper.manual_cache(uncached_source)

        if not cache_assist_module:
            g.notification(g.ADDON_NAME, g.get_language_string(30186), time=3000)
            return

        cache_status = cache_assist_module.do_cache()

        if cache_status['result'] == 'success':
            self.cached_source = cache_status['source']
            self.close()
        elif cache_status['result'] == 'background':
            g.notification(g.ADDON_NAME, g.get_language_string(30468), time=3000)

    def handle_action(self, action_id, control_id=None):
        if action_id == 117:
            menu_items = []
            if self._filter_applied:
                menu_items.append(g.get_language_string(30694))
            else:
                menu_items.append(g.get_language_string(30693))

            response = xbmcgui.Dialog().contextmenu(menu_items)
            if response == 0:
                self.toggle_filter()

        if action_id == 7:
            if control_id == 1000:
                try:
                    self._cache_item()
                except (GeneralCachingFailure, FailureAtRemoteParty) as e:
                    g.log(e, 'error')
                    g.notification(g.ADDON_NAME, g.get_language_string(30032), time=3000)
            elif control_id == 2002:
                self.toggle_filter()
            elif control_id == 2999:
                self.close()

    def doModal(self):
        super().doModal()
        return self.cached_source
