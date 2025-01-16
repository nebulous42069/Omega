# -*- coding: utf-8 -*-

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['anymovie.cc', 'allmovies.gg', 'allmoviesforyou.net', 'allmoviesforyou.co']
        self.base_link = 'https://anymovie.cc'
        self.search_link = '/?s=%s'


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
            if url == None:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            aliases = eval(data['aliases'])
            title = data['tvshowtitle'] if 'tvshowtitle' in data else data['title']
            season, episode = (data['season'], data['episode']) if 'tvshowtitle' in data else ('0', '0')
            year = data['premiered'].split('-')[0] if 'tvshowtitle' in data else data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            search_html = client.scrapePage(search_url).text
            try:
                r = client_utils.parseDOM(search_html, 'article', attrs={'class': 'TPost B'})
                r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'h2', attrs={'class': 'Title'}), client_utils.parseDOM(i, 'span', attrs={'class': 'Qlty Yr'})) for i in r]
                r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year, data['year'])][0]
            except:
                r = client_utils.parseDOM(search_html, 'article')
                r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'h2', attrs={'class': 'title'}), client_utils.parseDOM(i, 'span', attrs={'class': 'tag'})) for i in r]
                r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
                url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year, data['year'])][0]
            if 'tvshowtitle' in data:
                url = url[:-1] if url.endswith('/') else url
                url = url.replace('/series/', '/episode/')
                url = url + '-%sx%s/' % (season, episode)
            page_html = client.scrapePage(url).text
            try:
                qual = client_utils.parseDOM(page_html, 'span', attrs={'class': 'Qlty'})[0]
            except:
                qual = ''
            results = client_utils.parseDOM(page_html, 'iframe', ret='src')
            for result in results:
                try:
                    if 'youtube.com' in result:
                        continue
                    result = client_utils.replaceHTMLCodes(result)
                    result_html = client.scrapePage(result).text
                    links = client_utils.parseDOM(result_html, 'iframe', ret='src')
                    for link in links:
                        try:
                            link = client_utils.replaceHTMLCodes(link)
                            for source in scrape_sources.process(hostDict, link, info=qual):
                                if scrape_sources.check_host_limit(source['source'], self.results):
                                    continue
                                self.results.append(source)
                        except:
                            #log_utils.log('sources', 1)
                            pass
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


