# -*- coding: utf-8 -*-

import re
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
        self.domains = ['alluc.co']
        self.base_link = 'https://alluc.co'
        #self.search_link = '/search/%s.html'
        self.notes = 'search seems to be blocked and the final links seem to goto a gomo error page lol.'


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
            #search_url = self.base_link + self.search_link % cleantitle.get_plus(title)
            cookie = client.request(self.base_link, output='cookie', timeout='5')
            ##
            title = cleantitle.geturl(title)
            if 'tvshowtitle' in data:
                epi_title = cleantitle.geturl(data['title'])
                url = self.base_link + '/watch-episode/%s-season-%s-episode-%s-%s' % (title, int(season), int(episode), epi_title)
            else:
                url = self.base_link + '/watch-movies/%s.html' % title
            ##
            #html = client.request(search_url, cookie=cookie, timeout='6')
            #r = client_utils.parseDOM(html, 'div', attrs={'class': 'ml-item'})
            #r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'img', attrs={'class': 'lazy thumb mli-thumb'}, ret='alt'), re.findall(r'<b>Release:\s*(\d{4})</b>', i)) for i in r]
            #r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            #url = [i[0] for i in r if cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year, data['year'])][0]
            #if 'tvshowtitle' in data:
                #sepi = '-season-%s-episode-%s/' % (int(season), int(episode))
                #url = self.base_link + url.replace('/watch-tv/', '/watch-episode/').replace('.html', sepi)
            #else:
                #url = self.base_link + url
            r = client.request(url, cookie=cookie, timeout='6')
            v = re.findall(r'document.write\(Base64.decode\("(.+?)"\)', r)[0]
            b64 = base64.b64decode(v)
            b64 = ensure_text(b64, errors='ignore')
            try:
                link = client_utils.parseDOM(b64, 'iframe', ret='src')[0]
            except:
                link = client_utils.parseDOM(b64, 'a', ret='href')[0]
            link = self.base_link + link.replace('\/', '/').replace('///', '//')
            link = client.request(link, cookie=cookie, output='geturl', timeout='6')
            for source in scrape_sources.process(hostDict, link):
                self.results.append(source)
            return self.results
        except:
            #log_utils.log('sources', 1)
            return self.results


    def resolve(self, url):
        return url


