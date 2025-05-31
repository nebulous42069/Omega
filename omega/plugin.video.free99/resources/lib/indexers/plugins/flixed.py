# -*- coding: utf-8 -*-

import simplejson as json
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
        self.base_link = 'https://flixed.io'
        self.channels_link = self.base_link + '/tv-guide/'
        self.channel_link = self.base_link + '/tv-guide/channels/'
        self.image_link = 'https://adma.tmsimg.com/assets/%s.png?w=360&h=270?w=100'
        self.base_image_link = 'https://flixed.vercel.app/images/flixed.png'
        self.channels_list = [
            ('A&E (AETV)', 'aetv', 's10035_ll_h3_ab'),  #'s10035_ll_h15_ab'
            ('AMC (AMC)', 'amc', 's10021_ll_h3_ab'),  #'s10021_ll_h15_ab'
            ('AXS TV (AXSTV)', 'axstv', 's28506_ll_h15_aa'),
            ('BBC America (BBCA)', 'bbca', 's18332_ll_h3_aa'),  #'s18332_ll_h15_aa'
            ('BET (BET)', 'bet', 's10051_ll_h3_ac'),  #'s10051_ll_h15_ac'
            ('BET Her (BHER)', 'bher', 's14897_ll_h15_ab'),
            ('Bravo (BRAVO)', 'bravo', 's10057_ll_h3_ab'),  #'s10057_ll_h15_ab'
            ('BYU-TV (BYUTV)', 'byutv', 's21855_ll_h15_ab'),
            ('Cartoon Network (TOON)', 'toon', 's12131_ll_h3_aa'),  #'s12131_ll_h15_aa'
            ('Cinemax (MAX)', 'max', 's10120_ll_h3_ab'),  #'s10120_ll_h15_ab'
            ('CMT (CMTV)', 'cmtv', 's10138_ll_h3_ab'),  #'s10138_ll_h15_ab'
            ('Comedy Central (COMEDY)', 'comedy', 's10149_ll_h3_ab'),  #'s10149_ll_h15_ab'
            ('Comet (COMET)', 'comet', 's97051_ll_h15_ab'),
            ('Disney Channel (DISN)', 'disn', 's10171_ll_h3_ae'),  #'s10171_ll_h15_ae'
            ('Disney Junior (DJCH)', 'djch', 's74796_ll_h15_ac'),
            ('Disney XD (DXD)', 'dxd', 's18279_ll_h3_aa'),  #'s18279_ll_h15_aa'
            ('Epix HD (EPIXHD)', 'epixhd', 's65687_ll_h15_af'),
            ('EPIX 2 HD (EPIX2HD)', 'epix2hd', 's67929_ll_h15_ac'),
            ('Epix Drive-in HD (EPDVNHD)', 'epdvnhd', 's103828_ll_h15_ac'),
            ('Epix Hits (EPIXHIT)', 'epixhit', 's74073_ll_h15_ac'),
            ('Fox (FOX)', 'fox', 's10212_h3_aa'),  #'s10212_h3_ba'
            ('Freeform (FREEFRM)', 'freefrm', 's10093_ll_h3_ad'),  #'s10093_ll_h15_ad'
            ('Fubo Movie Network (FUBOMN)', 'fubomn', 'None'),
            ('Fuse (FUSE)', 'fuse', 's14929_h3_aa'),
            ('FX (FX)', 'fx', 's14988_ll_h3_aa'),  #'s14321_ll_h15_aa'
            ('FXM (FXM)', 'fxm', 's14988_ll_h3_aa'),  #'s14988_ll_h15_aa'
            ('FXX (FXX)', 'fxx', 's17927_h3_aa'),  #'s17927_ll_h15_aa'
            ('Galavision Cable Network (GALA)', 'gala', 's10222_ll_h3_ab'),  #'s10222_ll_h15_ab'
            ('Hallmark Channel (HALL)', 'hall', 's11221_ll_h3_aa'),  #'s11221_ll_h15_aa'
            ('Hallmark Drama (HALLDR)', 'halldr', 's105723_ll_h15_aa'),
            ('Hallmark Movies & Mysteries HD (HMMHD)', 'hmmhd', 's46710_ll_h15_aa'),
            ('HBO (HBO)', 'hbo', 's10240_ll_h3_aa'),  #'s10240_ll_h15_aa'
            ('HBO2 (HBO2)', 'hbo2', 's10241_ll_h3_aa'),  #'s10241_ll_h15_aa'
            ('HBO Comedy HD (HBOCHD)', 'hbochd', 's59839_h3_aa'),
            ('HBO Family (HBOF)', 'hbof', 's16585_ll_h3_aa'),  #'s16585_ll_h15_aa'
            ('HBO Latino (HBOLAT)', 'hbolat', 's24553_h3_aa'),
            ('HBO Signature (HBOSIG)', 'hbosig', 's10243_h3_aa'),  #'s10243_h3_ba'
            ('HBO Zone HD (HBOZHD)', 'hbozhd', 's59845_ll_h15_aa'),
            ('History (HISTORY)', 'history', 's14771_ll_h3_ad'),  #'s14771_h3_ba'
            ('IFC (IFC)', 'ifc', 's14873_ll_h3_ac'),  #'s14873_ll_h15_ac'
            ('INSP (INSP)', 'insp', 's11066_ll_h9_ab'),
            ('Lifetime (LIFE)', 'life', 's10918_ll_h3_ac'),  #'s10918_ll_h15_ac'
            ('LMN (LMN)', 'lmn', 's18480_ll_h3_ad'),  #'s18480_ll_h15_ad'
            ('MavTV HD (MAVTVHD)', 'mavtvhd', 's61036_ll_h15_ab'),
            ('MoreMAX (MOMAX)', 'momax', 's10121_h3_aa'),  #'s10121_ll_h15_ad'
            ('MTV - Music Television (MTV)', 'mtv', 's10986_ll_h3_aa'),  #'s10986_ll_h15_aa'
            ('Nick Jr (NICJR)', 'nicjr', 's19211_ll_h3_aa'),  #'s19211_h3_aa'
            ('Nickelodeon (NIK)', 'nik', 's11006_ll_h3_aa'),  #'s11006_ll_h15_aa'
            ('Nicktoons (NIKTON)', 'nikton', 's30420_ll_h15_aa'),
            ('Outside Television HD (OUTSIDE)', 'outside', 's68295_ll_h9_aa'),
            ('Ovation (OVATION)', 'ovation', 's15807_ll_h15_ac'),
            ('Paramount Network (PAR)', 'par', 's11163_ll_h3_ac'),  #'s11163_ll_h15_ac'
            ('PBS (PBS)', 'pbs', 's11039_ll_h3_ab'),  #'s11039_ll_h15_ab'
            ('POP (POPSD)', 'popsd', 's16715_ll_h3_aa'),  #'s16715_ll_h15_aa'
            ('SHO 2 (SHO2)', 'sho2', 's11116_ll_h3_ac'),  #'s11116_ll_h15_aa'
            ('SHO x BET (SHOBET)', 'shobet', 's20622_ll_h15_ad'),
            ('Showtime (SHOW)', 'show', 's11115_ll_h3_ac'),  #'s11115_ll_h15_ac'
            ('Showtime Extreme (SHOWX)', 'showx', 's18086_ll_h3_ac'),  #'s18086_ll_h15_ac'
            ('Showtime Familyzone HD (FAMZHD)', 'famzhd', 's25274_ll_h15_ac'),
            ('Showtime Next HD (NEXTHD)', 'nexthd', 's68342_ll_h15_aa'),
            ('Showtime Showcase (SHOCSE)', 'shocse', 's16153_h3_aa'),  #'s16153_ll_h15_ac'
            ('Showtime Women HD (WOMENHD)', 'womenhd', 's68338_ll_h15_aa'),
            ('Sony Cine (SOCINH)', 'socinh', 's109720_ll_h15_aa'),
            ('Sony Movie Channel HD (SONYHD)', 'sonyhd', 's69130_ll_h15_ab'),
            ('Starz (STARZ)', 'starz', 's12719_ll_h3_ab'),  #'s12719_ll_h15_ab'
            ('Starz Cinema HD (STRZCIH)', 'strzcih', 's67236_ll_h15_ab'),
            ('Starz Comedy HD (STZCHD)', 'stzchd', 's57569_ll_h15_ab'),
            ('Starz Edge (STZE)', 'stze', 's16311_h3_aa'),
            ('Starz Encore (STZENC)', 'stzenc', 's10178_ll_h3_ab'),  #'s10178_ll_h15_ab'
            ('Starz Encore Classic (STZENCL)', 'stzencl', 's14764_ll_h15_ab'),
            ('Starz in Black (STZIB)', 'stzib', 's16833_ll_h15_ab'),
            ('Starz Kids (STZK)', 'stzk', 's19635_ll_h15_ab'),
            ('SundanceTV (SUNDANC)', 'sundanc', 's16108_ll_h3_aa'),  #'s16108_ll_h9_aa'
            ('Syfy (SYFY)', 'syfy', 's11097_ll_h3_ae'),  #'s11097_ll_h15_ae'
            ('TBS (TBS)', 'tbs', 's11867_ll_h3_ac'),  #'s11867_h3_aa'
            ('Teen Nick HD (TNCKHD)', 'tnckhd', 's97047_h3_aa'),
            ('Telemundo Television Network (TELE)', 'tele', 's10239_h3_aa'),  #'s10239_ll_h15_ab'
            ('The Movie Channel (TMC)', 'tmc', 's11160_ll_h3_aa'),  #'s11160_ll_h15_aa'
            ('The Movie Channel Extra (TMCX)', 'tmcx', 's17663_ll_h3_aa'),  #'s17663_ll_h15_aa'
            ('TNT (TNT)', 'tnt', 's11164_ll_h3_ac'),  #'s11164_ll_h15_ac'
            ('Turner Classic Movies (TCM)', 'tcm', 's12852_ll_h3_aa'),  #'s12852_ll_h15_ab'
            ('TV ONE (TVONE)', 'tvone', 's35513_ll_h3_ab'),  #'s35513_ll_h15_ab'
            ('UniMas (UNIMAS)', 'unimas', 's29058_ll_h3_aa'),  #'s29058_ll_h15_ab'
            ('Universal Kids HD (UKIDSH)', 'ukidsh', 's70225_ll_h15_ae'),
            ('Universo HD (UNVSOHD)', 'unvsohd', 's91588_ll_h15_ab'),
            ('Univision Network (UNI)', 'uni', 's11118_ll_h3_ab'),  #'s11118_ll_h15_ab'
            ('UPtv HD (UPHD)', 'uphd', 's66143_ll_h15_ac'),
            ('USA Network (USA)', 'usa', 's11207_ll_h3_ae'),  #'s11207_ll_h15_af'
            ('VH1 (VH1)', 'vh1', 's11218_ll_h3_aa'),  #'s11218_ll_h15_ab'
            ('Vice (VICE)', 'vice', 's18822_ll_h3_ac'),  #'s18822_ll_h15_ac'
            ('WAPA America (WAPAUS)', 'wapaus', 's63389_ll_h15_ab')
        ]


    def root(self):
        try:
            for i in self.channels_list:
                title = client_utils.replaceHTMLCodes(i[0])
                url = self.channel_link + i[1]
                if i[2] == 'None':
                    image = self.base_image_link
                else:
                    image = self.image_link % i[2]
                self.list.append({'title': title, 'url': url, 'image': image, 'action': 'flixed_scrape_channel'})
            navigator.navigator().addDirectory(self.list)
            return self.list
        except Exception:
            return self.list


    def get_movie(self, i):
        try:
            query = '%s&year=%s' % (quote_plus(i[0]), i[1])
            url = movies.movies().tmdb_search_link % query
            item = movies.movies().get(url, create_directory=False)[0]
            self.list.append(item)
        except Exception:
            pass


    def scrape_channel(self, url):
        try:
            html = client.scrapePage(url).text
            results = client_utils.parseDOM(html, 'script', attrs={'id': '__NEXT_DATA__'})[0]
            results = json.loads(str(results))
            results = results.get('props', {}).get('pageProps', {}).get('airings', [])
            for result in results:
                try:
                    if not result.get('program', {}).get('subType') == "Feature Film":
                        continue
                    title = result.get('program', {}).get('title')
                    title = client_utils.replaceHTMLCodes(title)
                    year = result.get('program', {}).get('releaseYear')
                    check = (title, year)
                    if check in self.items:
                        continue
                    self.items.append((title, year))
                except:
                    pass
            threads = []
            for i in range(0, len(self.items)):
                threads.append(workers.Thread(self.get_movie, self.items[i]))
            [i.start() for i in threads]
            [i.join() for i in threads]
            movies.movies().movieDirectory(self.list)
            return self.list
        except Exception:
            return self.list


