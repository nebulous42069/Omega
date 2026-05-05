from jurialmunkey.plugin import KodiPlugin
from jurialmunkey.parser import reconfigure_legacy_params


KODIPLUGIN = KodiPlugin('script.wikipedia')
ADDONPATH = KODIPLUGIN._addon_path


def do_wikipedia_gui(wikipedia, tmdb_type=None, xml_file=None, language=None, **kwargs):
    if not wikipedia:
        import xbmcgui
        wikipedia = xbmcgui.Dialog().input(heading='Wikipedia')
    if not wikipedia:
        return

    from lib.api import WikipediaGUI
    ui = WikipediaGUI(
        xml_file or 'script-wikipedia.xml', ADDONPATH, 'default', '1080i',
        query=wikipedia, tmdb_type=tmdb_type, language=language)
    ui.doModal()
    del ui


def do_wikipedia_language(**kwargs):
    import xbmcgui
    from lib.api import WikipediaLanguagesAPI
    languages = WikipediaLanguagesAPI().all_wikipedia_languages
    languages = tuple(((k, f"{v['name']} ({v.get('localname')})") for k, v in languages.items()))
    x = xbmcgui.Dialog().select('Languages', tuple((f'{i[0]} - {i[1]}' for i in languages)))
    if x == -1:
        return
    KODIPLUGIN.set_setting('language', languages[x][0], 'str')
    return


class Script():
    def __init__(self, *args):
        self.params = {}
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                self.params[key] = value.strip('\'').strip('"') if value else None
            else:
                self.params[arg] = True
        self.params = reconfigure_legacy_params(**self.params)

    routing_table = {
        'wikipedia': lambda **kwargs: do_wikipedia_gui(**kwargs),
        'set_language': lambda **kwargs: do_wikipedia_language(**kwargs)
    }

    def router(self):
        try:
            routes_available = set(self.routing_table.keys())
            params_given = set(self.params.keys())
            route_taken = set.intersection(routes_available, params_given).pop()
            route = self.routing_table[route_taken]
        except KeyError:
            return do_wikipedia_gui(None)
        route(**self.params)
