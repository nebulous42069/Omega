# -*- coding: utf-8 -*-

# Author/Copyright: fr33p0rt
# License: GPLv3 https://www.gnu.org/copyleft/gpl.html

from __future__ import absolute_import, division, unicode_literals

import requests
from bs4 import BeautifulSoup

class Pornky:
    URL = 'https://www.pornky.club/'
    URL_CAT = '%s%s' % (URL, 'categories/')
    URL_SEARCH = '%s%s' % (URL, 'search/?q=%s')
    URL_LOGIN = '%s%s' % (URL, 'login.php')
    cookies = None
    categories = []
    main_menu = []
    log_menu = []
    videos = []
    root_page = ''
    categories_page = ''
    last_status_code = None

    def set_resolution(self, resolution_limit):
        pass

    def filter_category(self, categories, type):
        """
        Set category filter

        :param categories: list of categories (str)
        :type categories: str
        :param type: type of filter ('remove' 'only' 'ignore')
        :type type str
        """
        pass

    def login(self, username, password):
        # headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': self.URL, 'X-Requested-With': 'XMLHttpRequest'}
        payload = {'action': 'login', 'format': 'json', 'mode': 'async', 'username': username, 'pass': password}
        #r = requests.post(self.URL_LOGIN, cookies=self.get_cookies(), data=payload, verify=False)
        r = requests.post(self.URL_LOGIN, data=payload, verify=False)
        if '"status":"success"'.encode('utf-8') not in r.content:
            return
        return r.cookies

    def set_cookies(self, cfg):
        if cfg.disable_login:
            self.get_cookies()
            return False, {}
        logged_in = False
        if cfg.cookie_PHPSESSID:
            self.cookies = {'PHPSESSID': cfg.cookie_PHPSESSID}
            r = self.get_root_page()
            #r = requests.get(self.URL, verify=False)
            logged_in = '/my_favourite_videos/' in r
            if logged_in:
                return True, {}
        if cfg.username and cfg.password and not logged_in:
            self.cookies = {}
            self.root_page = ''
            self.get_root_page()
            cookies2 = self.login(cfg.username, cfg.password)
            if cookies2:
                self.cookies = requests.cookies.merge_cookies(self.cookies, cookies2)
                self.root_page = ''
                r = self.get_root_page()
                logged_in = '/my_favourite_videos/' in r
            if logged_in:
                return True, self.cookies
        return False, {}

    def get_cookies(self):
        """
        Initializes cookies
        """
        if not self.cookies:
            self.cookies = requests.head(self.URL, verify=False).cookies
        return self.cookies

    def get_root_page(self):
        """
        Returns root page
        """
        if not self.root_page:
            r = requests.get(self.URL, cookies=self.get_cookies(), verify=False)
            self.root_page = r.text
            self.last_status_code = r.status_code
        return self.root_page

    def get_categories_page(self):
        """
        Returns page with categories
        """
        if not self.categories_page:
            self.categories_page = requests.get(self.URL_CAT, cookies=self.get_cookies(), verify=False).text
        return self.categories_page

    def get_log_menu(self):
        """
        Returns log menu item 'My favourite videos' from root page
        """
        if not self.log_menu:
            soup = BeautifulSoup(self.get_root_page(), 'html.parser').find('div', id="logmenu")
            if soup:
                cnt = 0
                for i in soup.find_all('a'):
                    if i.get('title') == 'My favourite videos':
                        self.log_menu.append({'name': i.get('title') + ' ...', 'url': i.get('href')})
        return self.log_menu

    def get_main_menu(self):
        """
        Returns main menu items from root page
        """
        if not self.main_menu:
            soup = BeautifulSoup(self.get_root_page(), 'html.parser')
            for i in soup.find('div', class_="main_menu").find_all('a'):
                if i.get('id') and i.get('id')[0:4] == 'item' and i.get('id') != 'item1':
                    self.main_menu.append({'name': i.get('title'), 'url': i.get('href')})
        return self.main_menu

    def get_categories(self):
        """
        Returns categories items from categories page
        """
        if not self.categories:
            soup = BeautifulSoup(self.get_categories_page(), 'html.parser')
            for i in soup.find('div', class_='block_content').find_all('div', class_='item'):
                self.categories.append({'name': i.find('img').get('alt'),
                                        'url': i.find('a').get('href'),
                                        'thumb': i.find('img').get('src')+'|verifypeer=false'})
        return self.categories

    def get_video_links(self, url):
        """
        Returns video links from video page
        """
        soup = BeautifulSoup(self.get_page(url), 'html.parser')
        data = soup.find('div', id='player')

        data_id = data.get('data-id')
        data_s = data.get('data-s')
        data_q_list = data.get('data-q').split(',')
        data_t = data.get('data-t')
        data_n = data.get('data-n')

        default = '720p'
        video_links = []
        for data_q in data_q_list:
            _ = data_q.split(';')
            res_suffix = '_' + _[0] if default != _[0] else ''
            url = 'https://{}.vstor.top/whpvid/{}/{}/{}000/{}/{}{}.mp4'.format(
                data_n, _[4], _[5],
                str((int(data_id) // 1000)), data_id,
                data_id, res_suffix)
            video_links.append((int(''.join(x for x in _[0] if x.isdigit())), url))
        for _ in video_links:
            print(_)
        return video_links

#### https://s4.vstor.info/whpvid/1707511532/cDws6lLrP3pVvWAnJCRPNA/17000/17916/17916_480p.mp4

    def get_video_links_from_downloads(self, url):
        """
        Returns video links from video page
        """
        soup = BeautifulSoup(self.get_page(url), 'html.parser')
        soup_links = soup.find(id="plinks")
        data_c_list = []
        for i in soup_links.find_all('div'):
            if i.get('data-c'):
                data_c_list.append(i.get('data-c').split(';'))

        default = '720p'

        video_links = []
        for data_c in data_c_list:

            res_suffix = '_' + data_c[1] if default != data_c[1] else ''
            url = 'http://s{}.stormedia.info/whlvid/{}/{}/{}000/{}/{}{}.mp4/{}{}.mp4'.format(
                data_c[7], data_c[5], data_c[6],
                str((int(data_c[4]) // 1000)), data_c[4],
                data_c[4], res_suffix, data_c[4], res_suffix)

            video_links.append((int(''.join(x for x in data_c[1] if x.isdigit())), url))

        return video_links

    def get_video_link(self, url, max_resolution):
        video_links = self.get_video_links(url)
        video_links.sort(reverse=True)
        while len(video_links) > 1 and video_links[0][0] > max_resolution:
            video_links = video_links[1:]
        return video_links[0]

    def get_page(self, url):
        """
        Returns page
        """
        return requests.get(url, cookies=self.get_cookies(), verify=False).text

    def get_next_page(self, soup):
        """
        Returns link to next page from soup
        """
        page = soup.find('div', class_="pages")
        if not page:
            return None
        page = page.find('span')
        if not page:
            return None
        page = page.find_next_sibling()
        if page:
            return {'name': page.get('title'), 'url': page.get('href')}
        else:
            return None

    def get_video_categories(self, url):
        soup = BeautifulSoup(self.get_page(url), 'html.parser')
        categories = ''
        try:
            list_cat = []
            for i in soup.find('div', class_='videocats').find_all('a'):
                if i.string[0:3] == 'HD ':
                    list_cat.append(i.string[3:].replace(' Porno Videos', ''))
                else:
                    list_cat.append(i.string.replace(' Porno Videos', ''))
            categories = ', '.join(list_cat)
        except:
            pass
        return categories

    def get_videos(self, soup):
        """
        Returns all videos from soup tree
        """
        video_page_list = []
        for i in soup.find_all('div', class_="video"):
            name = i.find('h2').find('a').get('title')
            page = i.find('h2').find('a').get('href')
            thumb = i.find('img').get('src')
            #takes too long
            #categories = self.get_video_categories(page)
            duration = i.find('div', class_="duration").string
            video_page_list.append({'name': name, 'thumb': thumb, 'page': page, 'duration': duration, 'categories': 'Porn'})
        return video_page_list

    def get_videos_and_next_page(self, url):
        """
        Returns all videos and link to next page
        """
        soup = BeautifulSoup(self.get_page(url) if url[:4]=='http' else self.get_page(self.URL+url), 'html.parser')
        return (self.get_videos(soup), self.get_next_page(soup))
