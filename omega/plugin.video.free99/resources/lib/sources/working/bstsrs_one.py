# -*- coding: utf-8 -*-

import re
from six.moves.urllib_parse import parse_qs, urlencode

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import decryption
from resources.lib.modules import scrape_sources
# from resources.lib.modules import log_utils



class source:
    def __init__(self):
        self.results = [] # Might be able to use bstsrs.cc too but would need to look at it.
        self.domains = ['bstsrs.in', 'bstsrs.one', 'srstop.link']
        self.base_link = 'https://srstop.link'
        self.cookie = client.request(self.base_link, output='cookie', timeout='10')


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        if tvshowtitle == 'House':
            tvshowtitle = 'House M.D.'
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
        
    def decoder(self, uri):
        ALPHABET = {
        '19e0c88cb': '-', '19e0c88cc': '.', '19e0c88cd': '/',
        '19e0c88ce': '0', '19e0c88cf': '1', '19e0c88d0': '2', '19e0c88d1': '3',
        '19e0c88d2': '4', '19e0c88d3': '5', '19e0c88d4': '6', '19e0c88d5': '7',
        '19e0c88d6': '8', '19e0c88d7': '9', '19e0c88d8': ':',
        '19e0c88df': 'A', '19e0c88e0': 'B', '19e0c88e1': 'C', '19e0c88e2': 'D',
        '19e0c88e3': 'E', '19e0c88e4': 'F', '19e0c88e5': 'G', '19e0c88e6': 'H',
        '19e0c88e7': 'I', '19e0c88e8': 'J', '19e0c88e9': 'K', '19e0c88ea': 'L',
        '19e0c88eb': 'M', '19e0c88ec': 'N', '19e0c88ed': 'O', '19e0c88ee': 'P',
        '19e0c88ef': 'Q', '19e0c88f0': 'R', '19e0c88f1': 'S', '19e0c88f2': 'T',
        '19e0c88f3': 'U', '19e0c88f4': 'V', '19e0c88f5': 'W', '19e0c88f6': 'X',
        '19e0c88f7': 'Y', '19e0c88f8': 'Z', '19e0c88fd': '_',
        '19e0c88ff': 'a', '19e0c8900': 'b', '19e0c8901': 'c', '19e0c8902': 'd',
        '19e0c8903': 'e', '19e0c8904': 'f', '19e0c8905': 'g', '19e0c8906': 'h',
        '19e0c8907': 'i', '19e0c8908': 'j', '19e0c8909': 'k', '19e0c890a': 'l',
        '19e0c890b': 'm', '19e0c890c': 'n', '19e0c890d': 'o', '19e0c890e': 'p',
        '19e0c890f': 'q', '19e0c8910': 'r', '19e0c8911': 's', '19e0c8912': 't',
        '19e0c8913': 'u', '19e0c8914': 'v', '19e0c8915': 'w', '19e0c8916': 'x',
        '19e0c8917': 'y', '19e0c8918': 'z'
        }
        for key in ALPHABET.keys():
            uri = uri.replace(key, ALPHABET[key])
        return uri.replace('---', '-$DASH$-').replace('-', '').replace('$DASH$', '-')


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            data = parse_qs(url)
            data = dict([(i, data[i][0]) if data[i] else (i, '') for i in data])
            imdb, title, year = (data['imdb'], data['tvshowtitle'], data['year'])
            season, episode = (data['season'], data['episode'])
            url_title1 = '%s %s' % (title, year)
            url_title1 = cleantitle.geturl(url_title1)
            url_title2 = cleantitle.geturl(title)
            url_sepi = 's%02de%02d' % (int(season), int(episode))
            headers = {'User-Agent': client.UserAgent, 'Referer': self.base_link}
            search_url = f"{self.base_link}/show/{url_title2}-{url_sepi}/season/{int(season)}/episode/{int(episode)}"
            html = None
            html = client.scrapePage(search_url, headers=headers).text
            # not all shows have an IMDB rating. ie Bondsman
            if f'imdb.com/title/{imdb}/' not in html and 'not found' in html.lower():
                search_url = f"{self.base_link}/show/{url_title1}-{url_sepi}/season/{int(season)}/episode/{int(episode)}"
                html = client.scrapePage(search_url, headers=headers).text
            elif '0 links' in html.lower():
                search_url = f"{self.base_link}/show/{url_title1}-{url_sepi}/season/{int(season)}/episode/{int(episode)}"
                html = client.scrapePage(search_url, headers=headers).text
            if f'imdb.com/title/{imdb}/' not in html and 'not found' in html.lower():
                return self.results
            links = re.compile(r"window\.open\(dbneg\('(.+?)'\)", re.DOTALL).findall(html)
            for link in links:
                try:
                    link = self.decoder(link)  
                    #log_utils.log('link after =' + repr(link), 1)
                    for source in scrape_sources.process(hostDict, link):
                        if scrape_sources.check_host_limit(source['source'], self.results):
                            continue
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
        



