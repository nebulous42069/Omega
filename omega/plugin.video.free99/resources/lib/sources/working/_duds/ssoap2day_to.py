# -*- coding: utf-8 -*-

import re
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils

# Main domain source list is from  https://ssoapgate.com/
# Alt domains likely needing some changes made...  soap2day.tf  soap2daynew.com  soap2day.fo  soap2day.ski  soap2day.pics


class source:
    def __init__(self):
        self.results = []
        self.domains = ['old.ssoap2day.to', 'ssoap2day.to']
        self.base_link = 'https://old.ssoap2day.to'


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
            clean_title = cleantitle.geturl(title)
            if 'tvshowtitle' in data:
                r_url = self.base_link + '/watchseries/%s/%s/%s' % (clean_title, season, episode)
            else:
                r_url = self.base_link + '/watchmovies/%s' % clean_title
            r_html = client.scrapePage(r_url).text
            links = re.compile(r''':['"](.+?)['"]''', re.DOTALL).findall(r_html)
            for link in links:
                link = link.replace("\\", "")
                if '//streamgzzz.com/' in link:
                    link = link + '$$' + r_url
                if '//embed.embedz.click/' in link:
                    try:
                        html = client.scrapePage(link).text
                        vurls = client_utils.parseDOM(html, 'iframe', ret='src')
                        for vurl in vurls:
                            for source in scrape_sources.process(hostDict, vurl):
                                self.results.append(source)
                    except:
                        #log_utils.log('sources', 1)
                        pass
                else:
                    for source in scrape_sources.process(hostDict, link):
                        self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


