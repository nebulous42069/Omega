# -*- coding: utf-8 -*-

import re

from six.moves.urllib_parse import quote_plus

from resources.lib.indexers import navigator
from resources.lib.indexers import movies

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import control
from resources.lib.modules import workers

control.moderator()


class listings:
    def __init__(self):
        self.list = []
        self.items = []
        self.stations_link = 'https://www.tvpassport.com/tv-listings/stations/%s'
        self.movies_today_link = 'https://www.tvpassport.com/tv-listings/movies'
        self.logo_image_link = 'https://www.tvpassport.com/resource/img/'
        self.base_image_link = 'https://cdn.tvpassport.com/image/station/240x135/'
        self.channels_list = [
            ('Movies on TV Today Highlights', 'self.movies_today_link', 'tv-passport-logo.png'),
            ('5StarMax', '5-star-max-eastern/636', 'v2/s25620_h15_ad.png'),
            ('ActionMax', 'actionmax-eastern/1377', 'v2/s18433_h15_ad.png'),
            ('AMC', 'amc-eastern-feed/177$$$amc/35317', 'v2/s114759_h15_aa.png'),
            ('B4U Movies', 'b4u-movies-north-america/4006', 'v2/s25529_h9_ab.png'),
            ('BBC America', 'bbc-america-east/615', 'v2/s18332_h15_aa.png'),
            ('BET', 'bet-eastern-feed/323$$$bet-her/6837', 'v2/s10051_h15_ad.png'),
            ('Bounce', 'bounce-network/14312', 'v2/s73067_h15_ab.png'),
            ('Bravo', 'bravo-usa-eastern-feed/646', 'v2/s10057_h15_ab.png'),
            ('BYU', 'byu-brigham-young-university/3332', 'v2/s21855_h15_ab.png'),
            ('Cartoon Network', 'cartoon-network-usa-eastern-feed/661$$$cartoon-network-usa-pacific-feed/1209', 'v2/s12131_h15_aa.png'),
            ('Cine Estelar', 'cine-estelar/6830', 'v2/s62125_h15_aa.png'),
            ('Cine Latino', 'cinelatino-usa/3081', 'v2/s15296_h9_ab.png'),
            ('Cine Mexicano', 'cine-mexicano/4469', 'v2/s44714_h15_aa.png'),
            ('Cinemax', 'cinemax-eastern-feed/632$$$cinemax-pacific-feed/1215', 'v2/s10120_h15_ab.png'),
            ('Cinemax Latin', 'cinemax-latin/9962', 'v2/s25623_h15_ad.png'),
            ('CLEO TV', 'cleo-tv/33138', 'v2/s110288_h15_aa.png'),
            ('CMT', 'cmt-us-eastern-feed/1076', 'v2/s10138_h15_ab.png'),
            ('Comedy Central', 'comedy-central-us-eastern-feed/647', 'v2/s10149_h15_ab.png'),
            ('Comet TV', 'comet-tv/16811', 'v2/s97051_h15_ab.png'),
            ('Crave1-4', 'crave1-east/72$$$crave2-east/86$$$crave3-east/85$$$crave4/320', 'v2/s10191_h15_ab.png'),
            ('De Pelicula', 'de-pelicula/4419$$$de-pelicula-clasico/4420', 'v2/s16288_h15_ac.png'),
            ('Disney', 'disney-eastern-feed/595$$$disney-pacific-feed/1271', 'v2/s10171_h15_ae.png'),
            ('Disney Junior', 'disney-junior-usa-east/6867', 'v2/s74796_h15_ac.png'),
            ('Disney XD', 'disney-xd-usa-eastern-feed/1053', 'v2/s18279_h15_aa.png'),
            ('Documentary Channel', 'documentary-channel-canada/462', 'v2/s26784_h15_aa.png'),
            ('E! Entertainment', 'e-entertainment-usa-eastern-feed/617', 'v2/s10989_h15_aa.png'),
            ('El Rey Network', 'el-rey-network/11399', 'v2/s124328_h9_aa.png'),
            ('ELLE Fictions', 'elle-fictions/101', 'v2/s15675_h9_ac.png'),
            ('EPIX', 'epix-east/7609', 'v2/s65669_h15_ad.png'),
            ('EPIX2', 'epix2-east/11485', 'v2/s73075_h15_ac.png'),
            ('EPIX Drive-In', 'epix-drivein/11487', 'v2/s68409_h15_ac.png'),
            ('EPIX Hits', 'epix-hits/11486', 'v2/s74320_h15_ab.png'),
            ('FLIX', 'flix-eastern/1399', 'v2/s10201_h15_aa.png'),
            ('FMC Family Movie Classics', 'fmc-family-movie-classics/36900', 'v2/s122068_h15_aa.png'),
            ('Freeform', 'freeform-east-feed/1011', 'v2/s10093_h15_ad.png'),
            ('FUSE TV', 'fuse-tv-eastern-feed/1486', 'v2/s14929_h15_ac.png'),
            ('FX', 'fx-networks-east-coast/652', 'v2/s14321_h15_aa.png'),
            ('FX Movie Channel', 'fx-movie-channel/1308', 'v2/s70253_h15_aa.png'),
            ('FXX', 'fxx-usa-eastern/1952', 'v2/s17927_h15_aa.png'),
            ('GAC Family', 'gac-family-east/1051', 'v2/s16062_h15_ad.png'),
            ('Grit', 'grit-network/14377', 'v2/s89922_h9_aa.png'),
            ('Hallmark', 'hallmark-eastern-feed/1052', 'v2/s11221_h15_aa.png'),
            ('Hallmark Movies & Mysteries', 'hallmark-movies-mysteries-eastern/4453', 'v2/s61522_h15_aa.png'),
            ('HBO', 'hbo-eastern-feed/614$$$hbo-pacific-feed/1472', 'v2/s10240_h15_aa.png'),
            ('HBO 1', 'hbo1/84', 'v2/s61557_h15_ab.png'),
            ('HBO 2', 'hbo-2-eastern-feed/626$$$hbo-2-pacific-feed/2205', 'v2/s68140_h15_ad.png'),
            ('HBO Comedy', 'hbo-comedy-east/629', 'v2/s18429_h15_aa.png'),
            ('HBO Family', 'hbo-family-eastern-feed/628$$$hbo-family-pacific-feed/1216', 'v2/s16585_h15_aa.png'),
            ('HBO Latino', 'hbo-latino-hbo-7-eastern/631', 'v2/s24553_h9_ab.png'),
            ('HBO Signature', 'hbo-signature-hbo-3-eastern/1651', 'v2/s10243_h15_aa.png'),
            ('HBO Zone', 'hbo-zone-east/630', 'v2/s18431_h15_aa.png'),
            ('HDNet Movies', 'hdnet-movies/4267', 'v2/s33668_h15_ae.png'),
            ('Hollywood Suite 00s', 'hollywood-suite-00s/8887', 'v2/s73578_h15_aa.png'),
            ('Independent Film Channel', 'independent-film-channel-us/1966', 'v2/s14873_h15_ac.png'),
            ('INDIEplex', 'indieplex-eastern/2340', 'v2/s49751_h15_ab.png'),
            ('INSP', 'insp/1082', 'v2/s11066_h15_ac.png'),
            ('IVC Network', 'ivc-network-international/18867', 'v2/s97002_h15_aa.png'),
            ('Laff', 'laff-network/20169', 'v2/s92091_h15_aa.png'),
            ('Lifetime', 'lifetime-network-us-eastern-feed/654$$$lifetime-tv-canada/1148', 'v2/s10918_h15_ac.png'),
            ('Lifetime Movies', 'lifetime-movies-east/1333', 'v2/s18480_h15_ad.png'),
            ('Link TV', 'link-tv/3750', 'v2/s21450_h15_aa.png'),
            ('MAX', 'max/306', 'v2/s17591_h15_aa.png'),
            ('MGM', 'mgm-hd-usa/6107', 'v2/s58530_h15_aa.png'),
            ('MoreMax', 'moremax-eastern/634', 'v2/s10121_h15_ad.png'),
            ('MovieMax', 'moviemax-max-6-east/1653', 'v2/s25621_h15_ad.png'),
            ('MOVIEplex', 'movieplex-eastern/1066', 'v2/s15295_h15_aa.png'),
            ('Movies!', 'movies-kajrld-des-moines-ia/26055', 'v2/s81275_h15_ab.png'),
            ('MovieTime', 'movietime/464', 'v2/s27125_h15_aa.png'),
            ('Outdoor Life Network', 'outdoor-life-network-canada/160', 'v2/s17610_h15_ac.png'),
            ('OuterMax', 'outermax-eastern/2270', 'v2/s25622_h15_ab.png'),
            ('Paramount Network', 'paramount-network-usa-eastern-feed/1030$$$paramount-network-canada/3', 'v2/s11163_h15_ac.png'),
            ('RETROplex', 'retroplex-eastern/2342', 'v2/s49767_h15_aa.png'),
            ('Rewind', 'rewind/1149', 'v2/s27126_h15_aa.png'),
            ('Showtime', 'showtime-eastern-feed/665$$$showtime-west/10734', 'v2/s11115_h15_aa.png'),
            ('Showtime 2', 'showtime-2-eastern/1387', 'v2/s11116_h15_aa.png'),
            ('Showtime Extreme', 'showtime-extreme-eastern/1615', 'v2/s18086_h15_aa.png'),
            ('Showtime Family Zone', 'showtime-family-zone-eastern/1956', 'v2/s25274_h15_ac.png'),
            ('Showtime Next', 'showtime-next-eastern/2272', 'v2/s25270_h15_ac.png'),
            ('Showtime Showcase', 'showtime-showcase-eastern/2271', 'v2/s16153_h15_aa.png'),
            ('Showtime Women', 'showtime-women-eastern/2273', 'v2/s25272_h15_ac.png'),
            ('SHOxBET', 'shoxbet-eastern/2077', 'v2/s20622_h15_ad.png'),
            ('Silver Screen Classics', 'silver-screen-classics/2115', 'v2/s34290_h15_aa.png'),
            ('Slice', 'slice/60', 'v2/s15181_h15_ab.png'),
            ('Sony Cine', 'sony-cine/10967', 'v2/s109720_h15_aa.png'),
            ('Sony Movies', 'sony-movies/17063', 'v2/s69091_h15_ab.png'),
            ('Starz', 'starz-eastern/583$$$starz-pacific/1217', 'v2/s12719_h15_ab.png'),
            ('Starz1', 'starz1-east/55', 'v2/s14947_h15_ad.png'),
            ('Starz Cinema', 'starz-cinema-eastern/2680', 'v2/s19634_h15_ab.png'),
            ('Starz Comedy', 'starz-comedy-eastern/4223', 'v2/s34901_h15_ab.png'),
            ('Starz Edge', 'starz-edge-eastern/2120', 'v2/s16311_h15_ab.png'),
            ('Starz Encore', 'starz-encore-eastern/667$$$starz-encore-pacific/1218', 'v2/s10178_h15_ab.png'),
            ('Starz Encore Action', 'starz-encore-action-eastern/2078', 'v2/s14871_h15_ab.png'),
            ('Starz Encore Black', 'starz-encore-black-eastern/4206', 'v2/s14870_h15_ab.png'),
            ('Starz Encore Classic', 'starz-encore-classic-eastern/2080', 'v2/s14764_h15_ab.png'),
            ('Starz Encore Family', 'starz-encore-family-eastern/2128', 'v2/s14886_h15_ab.png'),
            ('Starz Encore Suspense', 'starz-encore-suspense-eastern/1958', 'v2/s14766_h15_ab.png'),
            ('Starz Encore Westerns', 'starz-encore-westerns-eastern/1959', 'v2/s14765_h15_ab.png'),
            ('Starz In Black', 'starz-in-black-eastern/1957', 'v2/s16833_h15_ab.png'),
            ('Starz Kids & Family', 'starz-kids-family-eastern/1194', 'v2/s19635_h15_ab.png'),
            ('Sun TV Tamil', 'sun-tv-tamil/13642', 'v2/s31634_h15_aa.png'),
            ('Super Channel Fuse', 'super-channel-fuse/4833', 'v2/s58870_h15_ab.png'),
            ('Super Channel Heart & Home', 'super-channel-heart-home/4834', 'v2/s58889_h15_ab.png'),
            ('Super Channel Vault', 'super-channel-vault/4835', 'v2/s58884_h15_ac.png'),
            ('Syfy', 'syfy-eastern-feed/596', 'v2/s11097_h15_ae.png'),
            ('ThrillerMax', 'thrillermax-east/1652', 'v2/s18435_h15_ad.png'),
            ('TMC', 'tmc-us-eastern-feed/666$$$tmc-us-pacific-feed/1222', 'v2/s11160_h15_aa.png'),
            ('TMC Xtra', 'tmc-xtra-eastern/4350$$$tmc-xtra-pacific/4351', 'v2/s17663_h15_aa.png'),
            ('TNT', 'tnt-eastern-feed/347', 'v2/s11164_h15_ac.png'),
            ('Turner Classic Movies', 'turner-classic-movies-usa/176$$$turner-classic-movies-canada/2847', 'v2/s12852_h15_ab.png'),
            ('TV Asia', 'tv-asia-canadian-feed/14212', 'v2/s76773_h9_ac.png'),
            ('TVA', 'tva-cftm-montreal/106', 'v2/s16367_h15_ab.png'),
            ('ViendoMovies', 'viendomovies/4470', 'v2/s52208_h15_aa.png'),
            ('W (WTN)', 'w-wtn-east/64', 'v2/s15024_h15_ab.png'),
            ('YTV', 'ytv-youth-television-east/15', 'v2/s12045_h9_ab.png')
        ]


    def root(self):
        try:
            for i in self.channels_list:
                if i[0] == 'Movies on TV Today Highlights':
                    action = 'tvpassport_movies_today_list'
                    image = self.logo_image_link + i[2]
                else:
                    action = 'tvpassport_stations_movies_list'
                    image = self.base_image_link + i[2]
                self.list.append({'title': client_utils.replaceHTMLCodes(i[0]), 'url': i[1], 'image': image, 'action': action})
            navigator.navigator().addDirectory(self.list)
            return self.list
        except Exception:
            return self.list


    def movies_items_list(self, i):
        try:
            query = '%s&year=%s' % (quote_plus(i[0]), i[1])
            url = movies.movies().tmdb_search_link % query
            item = movies.movies().get(url, create_directory=False)[0]
            self.list.append(item)
        except Exception:
            pass


    def stations_items_list(self, u):
        try:
            link = self.stations_link % u
            results = client.scrapePage(link, timeout='30').text
            results = re.findall('<strong>.+?">(.+?)</a> [(](\d{4})[)]</strong>', results)
            for result_t, result_y in results:
                try:
                    title = client_utils.replaceHTMLCodes(result_t)
                    year = result_y
                    check = (title, year)
                    if check in self.items:
                        continue
                    self.items.append((title, year))
                except:
                    pass
        except Exception:
            pass


    def stations_movies_list(self, url):
        try:
            threadsA = []
            if '$$$' in url:
                url = url.split('$$$')
                for u in url:
                    threadsA.append(workers.Thread(self.stations_items_list, u))
            else:
                threadsA.append(workers.Thread(self.stations_items_list, url))
            [i.start() for i in threadsA]
            [i.join() for i in threadsA]
            threadsB = []
            for i in range(0, len(self.items)):
                threadsB.append(workers.Thread(self.movies_items_list, self.items[i]))
            [i.start() for i in threadsB]
            [i.join() for i in threadsB]
            movies.movies().movieDirectory(self.list)
            return self.list
        except Exception:
            return self.list


    def movies_today_list(self, url):
        try:
            html = client.scrapePage(self.movies_today_link, timeout='30').text
            results = client_utils.parseDOM(html, 'h2', attrs={'class': 'h4'})
            results = [(client_utils.parseDOM(i, 'a'), client_utils.parseDOM(i, 'small')) for i in results]
            results = [(i[0][0], i[1][0]) for i in results if len(i[0]) > 0 and len(i[1]) > 0]
            for result in results:
                try:
                    title = result[0]
                    title = client_utils.replaceHTMLCodes(title)
                    year = result[1]
                    check = (title, year)
                    if check in self.items:
                        continue
                    self.items.append((title, year))
                except:
                    pass
            threads = []
            for i in range(0, len(self.items)):
                threads.append(workers.Thread(self.movies_items_list, self.items[i]))
            [i.start() for i in threads]
            [i.join() for i in threads]
            movies.movies().movieDirectory(self.list)
            return self.list
        except Exception:
            return self.list


