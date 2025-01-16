# -*- coding: utf-8 -*-

import base64
from six import ensure_text
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['cinecalidad.ec', 'cinecalidad.gg', 'cinecalidad.men', 'cinecalidad.vet', 'cinecalidad.run']
        self.base_link = 'https://www.cinecalidad.ec'
        self.search_link = '/?s=%s'
        self.notes = 'Ditched due to a lack of english sources.(results seem to be "Audio latino" so recoded without the english block could help someone else lol.)'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        url = {'imdb': imdb, 'tvshowtitle': tvshowtitle, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def episode(self, url, imdb, tmdb, tvdb, title, premiered, season, episode):
        if not url:
            return
        url = parse_qs(url)
        url = dict([(i, url[i][0]) if url[i] else (i, '') for i in url])
        url['title'], url['premiered'], url['season'], url['episode'] = title, premiered, season, episode
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            html = client.scrapePage(search_url).text
            results = client_utils.parseDOM(html, 'article', attrs={'class': 'item movies'})
            results = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', ret='alt')) for i in results]
            results = [(i[0][0], i[1][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0]
            result_url = [i[0] for i in results if cleantitle.match_alias(i[1], aliases)][0]
            if 'tvshowtitle' in data:
                check = 'S%s-E%s' % (season, episode)
                html = client.scrapePage(result_url).text
                results = client_utils.parseDOM(html, 'li', attrs={'class': 'mark-1'})
                results = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'div', attrs={'class': 'numerando'})) for i in results]
                results = [(i[0][0], i[1][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0]
                result_url = [i[0] for i in results if check == i[1]][0]
            html = client.scrapePage(result_url).text
            results = zip(client_utils.parseDOM(html, 'li', attrs={'class': r'dooplay_player_option.*?'}, ret='data-option'), client_utils.parseDOM(html, 'li', attrs={'class': r'dooplay_player_option.*?'}))
            for result_link, result_data in results:
                if not '/flags/en.png' in result_data:
                    continue
                if any(x in result_link for x in self.domains):
                    result_link = self.decode_url(result_link)
                if any(x in result_link for x in self.domains): # ran again because they are jews.
                    result_link = self.decode_url(result_link) # untouched result from cinecalidad.lol which likely needs resolved since /play/ is in the urls.
                if not result_link.startswith('http') or result_link.startswith('//'):
                    continue
                for source in scrape_sources.process(hostDict, result_link):
                    if scrape_sources.check_host_limit(source['source'], self.results):
                        continue
                    self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def decode_url(self, url):
        try:
            try:
                url = url.split('?i=')[1]
            except:
                pass
            try:
                url = url.split('?h=')[1]
            except:
                pass
            try:
                url = url.split('?id=')[1]
            except:
                pass
            try:
                url = url.split('&o=')[0]
            except:
                pass
            b64 = base64.b64decode(url)
            url = ensure_text(b64, errors='ignore')
        except:
            #log_utils.log('decode_url', 1)
            pass
        return url


    def resolve(self, url):
        return url


