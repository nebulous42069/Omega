# -*- coding: utf-8 -*-

import re

from resources.lib.modules import cleantitle
from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import scrape_sources
#from resources.lib.modules import log_utils


class source:
    def __init__(self):
        self.results = [] ## Mirror Holder  https://hollymoviehd-official.com/
        self.domains = ['novamovie.net'] # Alt domains:  nmovies.cc  yeshd.net
        self.base_link = 'https://novamovie.net'
        self.search_link = '/?s=%s'
        self.notes = 'Dupe of hollymoviehd_cc. Think the whole site has blockage, swap to "hard coded" urls since the search has blockage.'


    def movie(self, imdb, tmdb, title, localtitle, aliases, year):
        try:
            url = self.base_link + '/%s-%s/' % (cleantitle.get_dash(title), year)
            """
            movie_title = cleantitle.get_plus(title)
            check_title = '%s (%s)' % (title, year)
            check_title = cleantitle.get(check_title)
            movie_link = self.base_link + self.search_link % movie_title
            r = client.scrapePage(movie_link).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='title')) for i in r]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            url = [i[0] for i in r if check_title == cleantitle.get(i[1])][0]
            """
            return url
        except:
            #log_utils.log('movie', 1)
            return


    def tvshow(self, imdb, tmdb, tvdb, tvshowtitle, localtvshowtitle, aliases, year):
        try:
            url = tvshowtitle
            return url
        except:
            #log_utils.log('tvshow', 1)
            return


    def episode(self, url, imdb, tmdb, tvdb, title, premiered, season, episode):
        try:
            if not url:
                return
            url = self.base_link + '/episode/%s-season-%s-episode-%s/' % (cleantitle.get_dash(url), season, episode)
            """
            tvshow_title = cleantitle.get_plus(url)
            check_title = '%s Season %s' % (url, season)
            check_title = cleantitle.get(check_title)
            tvshow_link = self.base_link + self.search_link % tvshow_title
            r = client.scrapePage(tvshow_link).text
            r = client_utils.parseDOM(r, 'div', attrs={'class': 'ml-item'})
            r = [(client_utils.parseDOM(i, 'a', ret='href'), client_utils.parseDOM(i, 'a', ret='title')) for i in r]
            r = [(i[0][0], i[1][0]) for i in r if len(i[0]) > 0 and len(i[1]) > 0]
            url = [i[0] for i in r if check_title == cleantitle.get(i[1])][0]
            url = url.replace('/series/', '/episode/')
            url = url[:-1] if url.endswith('/') else url
            url = url + '-episode-%s/' % episode
            """
            return url
        except:
            #log_utils.log('episode', 1)
            return


    def sources(self, url, hostDict):
        try:
            if not url:
                return self.results
            html = client.scrapePage(url).text
            links = client_utils.parseDOM(html, 'a', attrs={'target': '_blank'}, ret='href')
            for link in links:
                try:
                    if link == '#' or any(x in link for x in ['facebook.com', 'imdb.com']):
                        continue
                    if 'getlinkstream.xyz' in link:
                        try:
                            html = client.scrapePage(link).text
                            vlinks = client_utils.parseDOM(html, 'a', ret='href')
                            for vlink in vlinks:
                                for source in scrape_sources.process(hostDict, vlink):
                                    if scrape_sources.check_host_limit(source['source'], self.results):
                                        continue
                                    self.results.append(source)
                        except:
                            #log_utils.log('sources', 1)
                            pass
                    if 'novalinks.online' in link:
                        try:
                            html = client.scrapePage(link).text
                            try:
                                qual = client_utils.parseDOM(html, 'title')[0]
                            except:
                                qual = ''
                            html = client_utils.parseDOM(html, 'div', attrs={'class': 'dlsvr-list'})
                            vlinks = client_utils.parseDOM(html, 'a', ret='href')
                            for vlink in vlinks:
                                for source in scrape_sources.process(hostDict, vlink, info=qual):
                                    if scrape_sources.check_host_limit(source['source'], self.results):
                                        continue
                                    self.results.append(source)
                        except:
                            #log_utils.log('sources', 1)
                            pass
                    else:
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


