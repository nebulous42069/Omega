import re
import xbmc
import xbmcgui
from bs4 import BeautifulSoup, Comment
from jurialmunkey.dialog import BusyDialog
from jurialmunkey.reqapi import RequestAPI
from jurialmunkey.plugin import KodiPlugin
from jurialmunkey.ftools import cached_property

USER_AGENT = f'Wikipedia for Kodi/0.2.0 (https://github.com/jurialmunkey/script.wikipedia jurialmunkey@kodi.tv) {xbmc.getUserAgent()}'

KODIPLUGIN = KodiPlugin('script.wikipedia')
get_localized = KODIPLUGIN.get_localized

ADDONDATA = 'special://profile/addon_data/script.wikipedia/'
get_infolabel = xbmc.getInfoLabel


WIKI_SCRL_ID = 61
WIKI_NAME_ID = 9901
WIKI_LIST_ID = 9902
WIKI_TEXT_ID = 9903
WIKI_ATTR_ID = 9904
WIKI_CCIM_ID = 9905
WIKI_ATTRIBUTION = f'{get_localized(32001)}\n{{}}'
WIKI_CCBYSA_IMG = 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/CC_BY-SA_icon.svg/320px-CC_BY-SA_icon.svg.png'
WIKI_UNABLE_TO_PARSE_TEXT = f'*** {get_localized(32000)} ***'

ACTION_CLOSEWINDOW = (9, 10, 92, 216, 247, 257, 275, 61467, 61448,)
ACTION_MOVEMENT = (1, 2, 3, 4, )
ACTION_SELECT = (7, )

DEFAULT_WIKI_LANGUAGE = 'en'

WIKI_TAG_LINK = '[COLOR=BF55DDFF]{}[/COLOR]'
WIKI_TAG_BOLD = '[B]{}[/B]'
WIKI_TAG_EMPH = '[LIGHT][I]{} [/I][/LIGHT]'
WIKI_TAG_SUPS = '[LIGHT]{}[/LIGHT]'


AFFIXES = {
    'tv': {
        'regex': r'\(TV series\)$',
        'affix': 'television series'
    },
    'movie': {
        'regex': r'\(Film\)$',
        'affix': 'film'
    },
    'person': {
        'regex': r'\(.*\)$',
        'affix': 'born'
    },
}


class RequestWikiAPI(RequestAPI):

    exit = False
    rate_limiter = 0

    def get_simple_api_request(self, request=None, postdata=None, headers=None, method=None):
        if method == 'delete':
            return self.session.delete(request, data=postdata, headers=headers, timeout=self.timeout)
        if method == 'put':
            return self.session.put(request, data=postdata, headers=headers, timeout=self.timeout)
        if method == 'json':
            return self.session.post(request, json=postdata, headers=headers, timeout=self.timeout)
        if method == 'json_delete':
            return self.session.delete(request, json=postdata, headers=headers, timeout=self.timeout)
        if postdata or method == 'post':  # If pass postdata assume we want to post
            return self.session.post(request, data=postdata, headers=headers, timeout=self.timeout)
        return self.session.get(request, headers=headers, timeout=self.timeout)

    def do_rate_limit_wait(self, retry_after, pdialog=True):
        self.rate_limiter = int(retry_after)
        pdialog = xbmcgui.DialogProgressBG() if pdialog else None
        pdialog.create(heading=f'Wikipedia') if pdialog else None
        monitor = xbmc.Monitor()
        waiting = self.rate_limiter
        cadence = 0.25

        while self.rate_limiter > 0 and not monitor.abortRequested() and not self.exit:
            pdialog.update(
                int((self.rate_limiter / waiting) * 100),
                message=f'Ratelimited - waiting {self.rate_limiter} seconds'
            ) if pdialog else None
            monitor.waitForAbort(cadence)
            self.rate_limiter -= cadence

        pdialog.close() if pdialog else None
        return bool(not monitor.abortRequested() and not self.exit)

    def get_api_request(self, request=None, postdata=None, headers=None, method=None):
        """
        Make the request to the API by passing a url request string
        """

        if self.rate_limiter > 0 and not self.do_rate_limit_wait(self.rate_limiter, pdialog=False):
            return

        # Get response
        response = self.get_simple_api_request(request, postdata, headers, method)
        if response is None or not response.status_code:
            return

        # Too many requests
        if response.status_code == 429:
            if not self.do_rate_limit_wait(response.headers['retry-after']):
                return
            return self.get_api_request(request, postdata, headers, method)

        # Other error
        if response.status_code >= 400:
            self.kodi_log([
                f'HTTP Error Code: {response.status_code}',
                f'\nRequest: {request.replace(self.req_api_key, "") if request else None}',
                f'\nPostdata: {postdata}' if postdata else '',
                f'\nHeaders: {headers}' if headers else '',
                f'\nResponse: {response}' if response else ''
            ], 2 if response.status_code == 404 else 1)
            return

        # Return our response
        return response


class WikimediaAPI(RequestWikiAPI):
    def __init__(self):
        super(WikimediaAPI, self).__init__(
            req_api_name='Wikimedia',
            req_api_url='https://commons.m.wikimedia.org/w/api.php')

    def get_request_lc(self, *args, **kwargs):
        kwargs['headers'] = {'User-Agent': USER_AGENT}
        return super().get_request_lc(*args, **kwargs)

    def get_titles(self, query):
        params = {
            'action': 'query', 'list': 'search', 'format': 'json',
            'srsearch': f'File: {query}'}
        data = self.get_request_lc(**params)
        if not data:
            return
        return [i['title'] for i in data['query']['search'] if i.get('title')]

    def get_images(self, titles):
        params = {
            'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'titles': '|'.join(titles),
            'iiprop': 'timestamp|user|userid|comment|canonicaltitle|url|size|dimensions|sha1|mime|thumbmime|mediatype|bitdepth'}
        return self.get_request_lc(**params)

    def get_backdrop(self, query):
        data = self.get_images(self.get_titles(query))
        for k, v in data['query']['pages'].items():
            for i in v.get('imageinfo', []):
                if i.get('width', 0) < 1280:
                    continue
                if i.get('width', 0) < i.get('height', 0):
                    continue
                if i.get('mime') != "image/jpeg":
                    continue
                if i.get('url'):
                    return i.get('url')


class WikimediaMetaAPI(RequestWikiAPI):
    def __init__(self):
        super(WikimediaMetaAPI, self).__init__(
            req_api_name='WikimediaMeta',
            req_api_url='https://meta.wikimedia.org/w/api.php')

    def get_request_lc(self, *args, **kwargs):
        kwargs['headers'] = {'User-Agent': USER_AGENT}
        return super().get_request_lc(*args, **kwargs)


class WikipediaLanguagesAPI(WikimediaMetaAPI):
    @cached_property
    def sitematrix(self):
        return self.get_request_lc(action='sitematrix', format='json')['sitematrix']

    @cached_property
    def sites(self):
        return tuple((v for v in self.sitematrix.values() if isinstance(v, dict)))

    def set_language_item(self, item, site):
        data = {k: v for k, v in item.items() if k != 'site'}
        data.update({f'site_{k}': v for k, v in site.items()})
        return data

    def get_languages_site_filter(self, **kwargs):
        return {
            item['code']: self.set_language_item(item, site)
            for item in self.sites
            for site in item['site']
            if all(site[k] == v for k, v in kwargs.items())
        }

    @cached_property
    def all_wikipedia_languages(self):
        return self.get_languages_site_filter(code='wiki')


class WikipediaAPI(RequestWikiAPI):
    def __init__(self, language=None):

        if not language or language not in self.wikipedia_languages:
            language = KODIPLUGIN.get_setting('language', 'str') or DEFAULT_WIKI_LANGUAGE

        self._wiki_tag_link = get_infolabel('Skin.String(Wikipedia.Format.Link)') or WIKI_TAG_LINK
        self._wiki_tag_bold = get_infolabel('Skin.String(Wikipedia.Format.Bold)') or WIKI_TAG_BOLD
        self._wiki_tag_emph = get_infolabel('Skin.String(Wikipedia.Format.Emphasis)') or WIKI_TAG_EMPH
        self._wiki_tag_sups = get_infolabel('Skin.String(Wikipedia.Format.Superscript)') or WIKI_TAG_SUPS

        super(WikipediaAPI, self).__init__(
            req_api_name='Wikipedia' if language == DEFAULT_WIKI_LANGUAGE else f'Wikipedia_{language}',
            req_api_url=f'https://{language}.wikipedia.org/w/api.php')

    @cached_property
    def wikipedia_languages(self):
        return WikipediaLanguagesAPI().all_wikipedia_languages

    def get_request_lc(self, *args, **kwargs):
        kwargs['headers'] = {'User-Agent': USER_AGENT}
        return super().get_request_lc(*args, **kwargs)

    def get_search(self, query, affix=None):
        params = {
            'action': 'query', 'format': 'json', 'list': 'search', 'utf8': 1,
            'srsearch': f'{query} {affix}' if affix else query}
        return self.get_request_lc(**params)

    def get_match(self, query, tmdb_type=None, match=''):
        affixes = AFFIXES.get(tmdb_type, {})
        affix = affixes.get('affix')
        _data = self.get_search(query, affix)
        items = [i['title'] for i in _data['query']['search']]
        if not items:
            xbmcgui.Dialog().ok(get_localized(32002), get_localized(32003).format(f'{query}'))
            return
        x = xbmcgui.Dialog().select('Wikipedia', items)
        if x == -1:
            return
        return items[x]

    def get_extract(self, title):
        params = {
            'action': 'query', 'format': 'json', 'titles': title, 'prop': 'extracts',
            'exintro': True, 'explaintext': True}
        return self.get_request_lc(**params)

    def get_sections(self, title):
        params = {
            'action': 'parse', 'page': title, 'format': 'json', 'prop': 'sections',
            'disabletoc': True, 'redirects': ''}
        try:
            return self.get_request_lc(**params)['parse']['sections']
        except (KeyError, AttributeError, TypeError):
            return []

    def get_fullurl(self, title):
        params = {'action': 'query', 'format': 'json', 'titles': title, 'prop': 'info', 'inprop': 'url'}
        try:
            data = self.get_request_lc(**params)['query']['pages']
            data = data[next(iter(data))]['fullurl']
        except (KeyError, AttributeError, TypeError):
            return ''
        return data

    @cached_property
    def section_cache(self):
        return {}

    def get_section(self, title, section_index):
        try:
            return self.section_cache[title][section_index]
        except KeyError:
            pass
        params = {
            'action': 'parse', 'page': title, 'format': 'json', 'prop': 'text',
            'disabletoc': True, 'section': section_index, 'redirects': '',
            'disablelimitreport': True,
            'disableeditsection': True,
            'mobileformat': True}
        data = self.get_request_lc(**params)
        if not data:
            return
        self.section_cache.setdefault(title, {})[section_index] = data
        return data

    def get_all_sections(self, title):
        sections = self.get_sections(title)
        sections = [{'line': 'Overview', 'index': '0', 'number': '0'}] + sections
        return sections

    def parse_links(self, data):
        raw_html = data['parse']['text']['*']
        soup = BeautifulSoup(raw_html, 'html.parser')
        links = [
            i['title'] for i in soup.find_all('a')
            if i.get('title')
            and i.get('href', '').startswith('/wiki/')
            and not i['title'].startswith('Help:')
            and not i['title'].startswith('Special:')
            and not i['title'].startswith('Wikipedia:')
            and not i['title'].startswith('Template:')
            and not i['title'].startswith('Category:')
            and not i.get('href', '').startswith('/wiki/File:')]
        return links

    def parse_image(self, data):
        raw_html = data['parse']['text']['*']
        soup = BeautifulSoup(raw_html, 'html.parser')
        links = [i for i in soup.find_all('img') if i.get('src')]
        return links

    def parse_text(self, data):
        raw_html = data['parse']['text']['*']
        soup = BeautifulSoup(raw_html, 'html.parser')
        text = []

        def _parse_table(p):
            for c in p.children:
                if isinstance(c, Comment):
                    continue
                if c.name in ['style']:
                    continue
                if c.name and any(x in ['mw-references-wrap', 'references-text', 'mw-editsection'] for x in c.get('class', [])):
                    continue
                if c.name in ['div', 'br']:
                    text.append(' ')
                elif c.name in ['p', 'table', 'tr', 'li']:
                    text.append('\n\n')
                if c.name == 'img' and c.get('title'):
                    text.append(f'{c["title"]}')
                    continue
                if c.string:
                    if c.string.startswith('^'):
                        continue
                    t = c.string.replace('\n', ' ')
                    if c.name in ['th', 'td']:
                        t = f'{t} '
                    if c.name and 'mw-headline' in c.get('class', ''):
                        t = self._wiki_tag_bold.format(t)
                    elif c.name in ['th', 'h2', 'b', 'h3', 'h1', 'h4']:
                        t = self._wiki_tag_bold.format(t)
                    elif c.name in ['i', 'em']:
                        t = self._wiki_tag_emph.format(t)
                    elif c.name in ['sup']:
                        t = self._wiki_tag_sups.format(t)
                    elif c.name in ['u', 'a']:
                        t = self._wiki_tag_link.format(t)
                    elif c.name in ['li']:
                        t = '* {}'.format(t)
                    text.append(f'{t}')
                    continue
                if c.children:
                    _parse_table(c)
                    continue

        _parse_table(soup)

        text = ''.join(text)
        text = re.sub(r'\[[0-9]*\]', '', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'( *\n){3,}', '\n\n', text)
        text = re.sub(r'^(\n)+', '', text)
        text = re.sub(r'^ +', '', text)
        text = re.sub(r'\n +', '\n', text)
        return text


class WikipediaGUIMeta:

    def __init__(self, language=None):
        self.language = language

    def close(self):
        self.wikipedia.exit = True
        self.wikimedia.exit = True
        del self.wikipedia
        del self.wikimedia

    @cached_property
    def wikipedia(self):
        return WikipediaAPI(language=self.language)

    @cached_property
    def wikimedia(self):
        return WikimediaAPI()

    def get_title(self, query, tmdb_type):
        return self.wikipedia.get_match(query, tmdb_type)

    @cached_property
    def overview(self):
        if not self.title:
            return
        data = self.wikipedia.get_section(self.title, '0')
        return self.wikipedia.parse_text(data)

    @cached_property
    def sections(self):
        if not self.title:
            return
        return self.wikipedia.get_all_sections(self.title)

    @cached_property
    def full_url(self):
        if not self.title:
            return
        return self.wikipedia.get_fullurl(self.title)

    @staticmethod
    def get_configured_section(section):
        name = section.get('line')
        indx = section.get('index')
        name = re.sub(r'<.*>', '', name)
        numb = section.get('number')
        name = f"{'    ' if '.' in numb else ''}{numb} {name}"
        return (name, indx)

    @cached_property
    def configured_sections(self):
        return tuple((
            (name, indx) for name, indx in (
                self.get_configured_section(section)
                for section in self.sections
            ) if name and indx
        ))

    @cached_property
    def listitems(self):
        return tuple((xbmcgui.ListItem(name) for name, indx in self.configured_sections))

    def get_image(self, x):
        try:
            data = self.wikipedia.get_section(self.title, f'{x}')
            imgs = self.wikipedia.parse_image(data)
        except (TypeError, AttributeError, KeyError, IndexError):
            return
        if not imgs:
            return
        for img in imgs:
            if int(img.get('width', 100)) < 32:
                continue
            if int(img.get('height', 100)) < 32:
                continue
            return img

    @cached_property
    def overview_img(self):
        return self.get_image(0)

    @cached_property
    def backdrop(self):
        return self.wikimedia.get_backdrop(self.title)

    def get_links(self, x):
        data = self.wikipedia.get_section(self.title, f'{x}')
        return self.wikipedia.parse_links(data)

    def get_section(self, x):
        # indx = i[1]
        data = self.wikipedia.get_section(self.title, f'{x}')
        text = self.wikipedia.parse_text(data)
        text = text or WIKI_UNABLE_TO_PARSE_TEXT
        return text


class WikipediaGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, query=None, tmdb_type=None, language=None, **kwargs):
        self.query = query
        self.tmdb_type = tmdb_type
        self.language = language
        self.do_setup()

    def do_setup(self, title=None):
        with BusyDialog():
            self.gui_meta = WikipediaGUIMeta(self.language)
            self.gui_meta.title = title or self.gui_meta.get_title(self.query, self.tmdb_type)
            if not self.gui_meta.title:
                return
            # Initialise some cached properties
            self.gui_meta.overview
            self.gui_meta.sections
            self.gui_meta.full_url

    @cached_property
    def history(self):
        return []

    def do_init(self):
        xbmcgui.Window(10000).clearProperty('Wikipedia.Backdrop')
        self.clearProperty('Backdrop')

        # Set basic details
        self._gui_name.setLabel(f'{self.gui_meta.title}')
        self._gui_text.setText(f'{self.gui_meta.overview}')
        self._gui_attr.setText(WIKI_ATTRIBUTION.format(self.gui_meta.full_url))
        self._gui_ccim.setImage(WIKI_CCBYSA_IMG)

        self.clearProperty('Image')

        # Set Sections
        self._gui_list.reset()
        self._gui_list.addItems(list(self.gui_meta.listitems))

        # Set focus on list first item
        self.setFocusId(WIKI_LIST_ID)
        self.set_section(0)

        # Set backdrop from wikimedia
        self.set_backdrop()

    def set_backdrop(self):
        if not self.gui_meta.backdrop:
            return
        xbmcgui.Window(10000).setProperty('Wikipedia.Backdrop', self.gui_meta.backdrop)
        self.setProperty('Backdrop', self.gui_meta.backdrop)

    def onInit(self):
        self._gui_name = self.getControl(WIKI_NAME_ID)
        self._gui_list = self.getControl(WIKI_LIST_ID)
        self._gui_text = self.getControl(WIKI_TEXT_ID)
        self._gui_attr = self.getControl(WIKI_ATTR_ID)
        self._gui_ccim = self.getControl(WIKI_CCIM_ID)
        if not self.gui_meta.title:
            self.close()
        self.do_init()

    def onAction(self, action):
        _action_id = action.getId()
        if _action_id in ACTION_CLOSEWINDOW:
            return self.do_close()
        if _action_id in ACTION_MOVEMENT:
            return self.do_scroll()
        if _action_id in ACTION_SELECT:
            return self.do_click()

    def onClick(self, control):
        if control == WIKI_LIST_ID:
            return self.do_scroll()

    def do_close(self):
        if self.getFocusId() == WIKI_SCRL_ID:
            return self.setFocusId(WIKI_LIST_ID)
        if not self.history:  # No history so close
            self.gui_meta.close()
            return self.close()
        self.do_setup(self.history.pop())  # History so go back instead
        self.do_init()

    def do_scroll(self):
        if self.getFocusId() != WIKI_LIST_ID:
            return
        self.set_section(self._gui_list.getSelectedPosition())

    def do_click(self):
        if self.getFocusId() not in [WIKI_SCRL_ID, WIKI_LIST_ID]:
            return

        links = self.gui_meta.get_links(self._gui_list.getSelectedPosition())
        if not links:
            return

        links = list(dict.fromkeys(links))
        x = xbmcgui.Dialog().select('Links', links)
        if x == -1:
            return

        self.history.append(self.gui_meta.title)
        self.do_setup(links[x])
        self.do_init()

    def set_image(self, x):
        data = self.gui_meta.get_image(x)
        data = data or self.gui_meta.overview_img
        if not data:
            return
        self.setProperty('Image', f'https:{data.get("src")}')
        self.setProperty('ImageText', f'{data.get("title") or data.get("alt")}')

    def set_section(self, x):
        text = self.gui_meta.get_section(x) if x else None
        if not text:
            return
        self._gui_text.setText(f'{text}')
        self.set_image(x)
