
import re
import requests
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
from resources.lib.modules import log_utils

import json   # ADDED
import base64 # ADDED
DOM = client_utils.parseDOM

class source:
    def __init__(self):
        self.results = []
        self.domains = ['gomovies.sx']
        self.base_link = 'https://gomovies.sx'
        self.search_link = '/search/%s'
        self.session = requests.Session()
        self.notes = 'Pulled in def from mbebe.'


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

    # written by mbebe on GitHub: https://github.com/mbebe/blomqvist
    # License: https://github.com/mbebe/blomqvist/blob/master/LICENSE
    #
    # TODO: should we move this into scrape_sources.py ?
    def GetPlayLink(self, server_id, url, host, headers):
        url_api = base64.b64decode(''.join(chr(int(c)) for c in
                                           '118O0O107O0O71O0O99O0O104O0O57O0O67O0O99O0O119O0O70O0O109O0O76O0O115O0O86O0O50O0O89O0O121O0O86O0O109O0O100O0O117O0O119O0O87O0O89O0O108O0O82O0O88O0O76O0O121O0O86O0O71O0O90O0O117O0O86O0O72O0O97O0O48O0O82O0O88O0O97O0O105O0O74O0O87O0O89O0O121O0O57O0O121O0O76O0O54O0O77O0O72O0O99O0O48O0O82O0O72O0O97'.split(
                                               'O0O'))[::-1]).decode('utf-8')
        id = server_id
        ref = url
        ref = self.base_link + ref if ref.startswith('/') else ref
        headers.update({'Referer': ref})
        get_url = self.base_link + '/ajax/sources/' + id
        
        # log_utils.log('get_url =' + repr(get_url), 1)
        response = requests.get(get_url, headers=headers, verify=None)
        json_data = None
        try:
            json_data = json.loads(response.text)
        except Exception as e:
            print(f"not json_data: {e}")

        if json_data:
            link = json_data['link']
        else:
            html = response.content
            html = html.decode(encoding='utf-8', errors='strict')
            link = re.findall('"link"\s*\:\s*"([^"]+)"', html, re.DOTALL)[0]

        nturl = link
        urlapi = url_api
        if 'vidcloud' in host:
            urlapi = url_api + 'vidcloud'
        elif 'upcloud' in host:
            urlapi = url_api + 'upcloud'

        if 'rabbitstream' in link:
            if '?z=' in nturl:
                nturl = nturl.split('?z=')[0]
            idx = nturl.split('/')[-1]  #
            ft = {'id': idx}
            response = requests.post(urlapi, data=ft, verify=None)
            html = response.content
            html = html.decode(encoding='utf-8', errors='strict')
            jsdata = json.loads(html)
            stream_url = jsdata['source']
        else:
            try:
                stream_url = link
            except:
                return link

        if stream_url:
            # log_utils.log('stream_url =' + repr(stream_url), 1)
            return stream_url

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
            search_url = self.base_link + self.search_link % cleantitle.geturl(title)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US, en;q=0.9',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'TE': 'Trailers',
            }

            r = client.scrapePage(search_url).text
            r = client_utils.clean_html(r)
            r = DOM(r, 'div', attrs={'class': 'flw-item'})
            r = [(DOM(i, 'a', ret='href'), DOM(i, 'a', ret='title'), DOM(i, 'span')) for i in r]
            r = [(i[0][0], i[1][0], i[2][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0 and len(i[2]) > 0]
            
            
            # TV shows don't include the year, so we have to do a second scrape.
            if 'tvshowtitle' in data:
                r2 = [(i[0], i[1], i[2]) for i in r if cleantitle.match_alias(i[1], aliases) and i[0].startswith('/tv/')]
                r2 = r2[::-1]   # reverse the list
                for link, t, s in r2:
                    yearCheckurl = self.base_link + link
                    r = client.scrapePage(yearCheckurl).text
                    get_year = re.findall('Released:.+?(\d{4})', r)[0]
                    check_year = cleantitle.match_year(get_year, year, data['year'])
                    if check_year:
                        url = yearCheckurl
                        break

            # MOVIE
            if not 'tvshowtitle' in data:
                result_url = [i[0] for i in r if
                              cleantitle.match_alias(i[1], aliases) and cleantitle.match_year(i[2], year) and i[0].startswith(
                                  '/movie/')][0]
                url = self.base_link + result_url
                if not url:
                    return
                r = client.scrapePage(url).text
                try:
                    check_year = re.findall('Released:.+?(\d{4})', r)[0]
                    check_year = cleantitle.match_year(check_year, year, data['year'])
                except:
                    check_year = 'Failed to find year info.'  # Used to fake out the year check code.
                    
            if not check_year:
                return self.results

            item_id = DOM(r, 'div', attrs={'class': 'detail_page-watch'}, ret='data-id')[0]
            if 'tvshowtitle' in data:
                check_season = 'Season %s' % season
                seasons_url = self.base_link + '/ajax/season/list/%s' % item_id
                r = client.scrapePage(seasons_url).text
                r = zip(DOM(r, 'a', ret='data-id'), DOM(r, 'a'))
                item_season_id = [i[0] for i in r if check_season == i[1]][0]
                check_episode = 'Eps %s:' % episode
                episodes_url = self.base_link + '/ajax/season/episodes/%s' % item_season_id
                r = client.scrapePage(episodes_url).text
                r = zip(DOM(r, 'a', ret='data-id'), DOM(r, 'a', ret='title'))
                item_episode_id = [i[0] for i in r if check_episode in i[1]][0]
                servers_url = self.base_link + '/ajax/episode/servers/%s/#servers-list' % item_episode_id
            else:
                servers_url = self.base_link + '/ajax/movie/episodes/%s' % item_id

            r = client.scrapePage(servers_url).text
            server_hosts = DOM(r, 'a', ret='title')
            server_hosts = [title.replace('Server ', '').lower() for title in server_hosts]
            if 'tvshowtitle' in data:
                server_ids = DOM(r, 'a', ret='data-id')
            else:
                server_ids = DOM(r, 'a', ret='data-linkid')
            servers = list(zip(server_ids, server_hosts))

            headers.update({'Referer': url})

            for server_id, host in servers:
                link = None
                try:
                    link = self.GetPlayLink(server_id, url, host, headers)
                except:
                    pass
                if 'upcloud' in host:
                    host = host + '.com'
                if link:
                    if not 'upcloud' in host:
                        for source in scrape_sources.process(hostDict, link, host=host):
                            self.results.append(source)
                    else:
                    # TODO: rework this so we use scrape_sources instead. Unsure if we are getting kicked out due to link provided
                        source = {
                                'source': host, 
                                'quality': 'SD',
                                'info': '',
                                'url': link,
                                'direct': False,
                                }
                        self.results.append(source)
                    
            return self.results

        except:
            return self.results


    def resolve(self, url):
        return url


