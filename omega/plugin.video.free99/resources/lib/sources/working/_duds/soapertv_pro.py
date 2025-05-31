# -*- coding: utf-8 -*-

import re
import requests

from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import cleantitle
from resources.lib.modules import scrape_sources
from resources.lib.modules import source_utils
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        try:
            self.results = []
            self.domains = ['soapertv.pro']
            self.base_link = 'https://soapertv.pro'
            self.search_link = '/?s=%s'
            self.ajax_link = '/wp-admin/admin-ajax.php'
            self.session = requests.Session()
            self.notes = 'Site loads super slow which makes it fail and so its a dud.'
        except Exception:
            #log_utils.log('__init__', 1)
            return


## Needs more work on sources bit.
# https://www.2embed.cc/embed/1029575


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        url = {'imdb': imdb, 'title': title, 'aliases': aliases, 'year': year}
        url = urlencode(url)
        return url


    def sources(self, url, hostDict):
        try:
            if url == None:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            title = data['title']
            year = data['year']
            search_title = cleantitle.get_plus(title)
            check_term = '%s (%s)' % (title, year)
            check_title = cleantitle.get_plus(check_term)
            search_url = self.base_link + self.search_link % search_title
            html = client.request(search_url)
            results = client_utils.parseDOM(html, 'div', attrs={'class': 'result-item'})
            results = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', ret='alt'), client_utils.parseDOM(i, 'span', attrs={'class': 'year'})) for i in results]
            results = [(i[0][0], i[1][0], i[2][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            result_url = [i[0] for i in results if check_title == cleantitle.get_plus(i[1]) and year == i[2]][0]
            html = client.request(result_url)
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
            results = re.compile(r"class='dooplay_player_option' data-type='(.+?)' data-post='(.+?)' data-nume='(.+?)'>", re.DOTALL).findall(html)
            for data_type, data_post, data_nume in results:
                try:
                    payload = {'action': 'doo_player_ajax', 'post': data_post, 'nume': data_nume, 'type': data_type}
                    r = self.session.post(post_link, headers=customheaders, data=payload)
                    i = r.json()
                    p = i['embed_url'].replace('\\', '')
                    link = scrape_sources.prepare_link(p)
                    if not link:
                        continue
                    #valid, host = source_utils.is_host_valid(link, hostDict)
                    #quality, info = source_utils.get_release_quality(link, link)
                    #link += '|%s' % urlencode({'Referer': self.base_link})
                    #self.results.append({'source': host, 'quality': quality, 'url': link, 'info': info, 'direct': True})
                    for source in scrape_sources.process(hostDict, link):
                        self.results.append(source)
                except:
                    #log_utils.log('sources', 1)
                    pass
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


