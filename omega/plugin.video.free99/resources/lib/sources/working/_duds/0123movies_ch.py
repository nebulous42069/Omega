# -*- coding: utf-8 -*-

import re
import requests

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = []
        self.domains = ['0123movies.lol', 'watch0123movies.net']
        self.base_link = 'https://0123movies.lol'
        self.search_link = '/?s=%s'
        self.ajax_link = '/wp-admin/admin-ajax.php'
        self.notes = 'Seems to have some form of blockage, so gotta look into it to make this one work again.'


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
            year = data['year']
            search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            html = client.scrapePage(search_url).text
            results = client_utils.parseDOM(html, 'div', attrs={'class': 'result-item'})
            results = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', ret='alt'), client_utils.parseDOM(i, 'span', attrs={'class': 'year'})) for i in results]
            results = [(i[0][0], i[1][0], i[2][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            result_url = [i[0] for i in results if cleantitle.match_alias(i[1], aliases) and year == i[2]][0]
            if 'tvshowtitle' in data:
                sepi1 = '-%sx%s-' % (season, episode)
                sepi2 = '-s%se%s-' % (season, episode)
                html = client.scrapePage(result_url).text
                results = client_utils.parseDOM(html, 'div', attrs={'class': 'episodiotitle'})
                results = [(client_utils.parseDOM(i, 'a', ret='href')) for i in results]
                result_url = [i[0] for i in results if sepi1 in i[0] or sepi2 in i[0]][0]
            html = client.scrapePage(result_url).text
            try:
                qual = client_utils.parseDOM(html, 'strong', attrs={'class': 'quality'})[0]
            except:
                qual = ''
            self.session = requests.Session()
            customheaders = {
                'Host': self.domains[0],
                'Accept': '*/*',
                'Origin': self.base_link,
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': client.UserAgent,
                'Referer': result_url,
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            post_link = self.base_link + self.ajax_link
            try:
                results = re.compile(r'''<li id='player-option(.+?)</li>''', re.DOTALL).findall(html)
                for result in results:
                    try:
                        if '/en.png' not in result:
                            continue
                        results = re.compile(r'''data-type=['"](.+?)['"] data-post=['"](.+?)['"] data-nume=['"](\d+)['"]>''', re.DOTALL).findall(result)
                        for data_type, data_post, data_nume in results:
                            try:
                                payload = {'action': 'doo_player_ajax', 'post': data_post, 'nume': data_nume, 'type': data_type}
                                r = self.session.post(post_link, headers=customheaders, data=payload)
                                i = r.text
                                p = i.replace('\\', '')
                                link = client_utils.parseDOM(p, 'iframe', ret='src')[0]
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
            except:
                #log_utils.log('sources', 1)
                pass
            try:
                tbody = client_utils.parseDOM(html, 'tbody')[0]
                tr = client_utils.parseDOM(html, 'tr')
                tr = [i for i in tr if 'English' in i]
                downloads = [(client_utils.parseDOM(i, 'a', attrs={'target': '_blank'}, ret='href'), client_utils.parseDOM(i, 'strong', attrs={'class': 'quality'})) for i in tr]
                downloads = [(i[0][0], i[1][0]) for i in downloads if len(i[0]) > 0 and len(i[1]) > 0]
                for download in downloads:
                    try:
                        link = client.request(download[0], timeout='6', output='geturl')
                        for source in scrape_sources.process(hostDict, link, info=download[1]):
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


