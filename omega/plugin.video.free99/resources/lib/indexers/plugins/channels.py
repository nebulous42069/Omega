# -*- coding: utf-8 -*-

import re
import simplejson as json
from six.moves.urllib_parse import quote_plus

from resources.lib.indexers import movies

from resources.lib.modules import client
from resources.lib.modules import client_utils
from resources.lib.modules import control
from resources.lib.modules import workers

control.moderator()


class channels:
    def __init__(self):
        self.list = []
        self.items = []
        ## Old link using  http:  with  now>next  at  level-3  detail.
        #self.sky_now_link = 'http://epgservices.sky.com/5.1.1/api/2.0/channel/json/%s/now/nn/3'
        ## New link using  https:  with  now>next>later  at  level-2  detail.
        self.sky_now_link = 'https://epgservices.sky.com/5.1.1/api/2.0/channel/json/%s/now/nnl/2'
        #(now>next>later can be  n nn nnl  as steps or stages.)(detail works from 2 to 4, but is 1 to 4.)


    def sky_list(self, channel, id):
        try:
            channel = channel.replace(' HD', '').replace('+', '')
            url = self.sky_now_link % id
            results = client.scrapePage(url, timeout='30').json()
            results = results['listings'][id]
            for result in results:
                try:
                    title = result['t']
                    title = client_utils.replaceHTMLCodes(title)
                    year = result['d']
                    year = re.findall('[(](\d{4})[)]', year)[0].strip()
                    check = (title, year, channel)
                    if check in self.items:
                        continue
                    self.items.append((title, year, channel))
                except:
                    pass
        except Exception:
            pass


    def items_list(self, i):
        try:
            query = '%s&year=%s' % (quote_plus(i[0]), i[1])
            url = movies.movies().tmdb_search_link % query
            item = movies.movies().get(url, create_directory=False)[0]
            item.update({'channel': i[2]})
            self.list.append(item)
        except Exception:
            pass


    def get(self):
        try:
            channels_list = [
                ('ActionWomen', '1811'), ('ActionWomen HD', '4020'),
                ('Christmas 24', '4420'), ('Christmas 24+', '4421'),
                ('Film4', '1627'), ('Film4 HD', '4044'), ('Film4+', '1629'),
                ('Horror Channel', '3605'), ('Horror Channel+', '4502'),
                ('ROK', '3542'),
                ('Sky Action', '1001'), ('Sky Action HD', '4014'),
                ('Sky Christmas', '1816'), ('Sky Christmas HD', '4016'),
                ('Sky Comedy', '1002'), ('Sky Comedy HD', '4019'),
                ('Sky Family', '1808'), ('Sky Family HD', '4018'),
                ('Sky Greats', '1815'), ('Sky Greats HD', '4015'),
                ('Sky Hits', '1814'), ('Sky Hits HD', '4033'),
                ('Sky Premiere', '1409'), ('Sky Premiere HD', '4021'), ('Sky Premiere+', '1823'),
                ('Sky ScFi/Horror', '1807'), ('Sky ScFi/Horror HD', '4017'),
                ('Sky Thriller', '1818'), ('Sky Thriller HD', '4062'),
                ('Sony Action', '3708'), ('Sony Action+', '3721'),
                ('Sony Christmas', '3643'), ('Sony Christmas+', '3751'),
                ('Sony Movies', '3709'), ('Sony Movies+', '3771'),
                ('TalkingPictures', '5252'),
                ('TCM Movies', '5605'), ('TCM Movies+', '5275')
            ]
            threads = []
            for i in channels_list:
                threads.append(workers.Thread(self.sky_list, i[0], i[1]))
            [i.start() for i in threads]
            [i.join() for i in threads]
            threads = []
            for i in range(0, len(self.items)):
                threads.append(workers.Thread(self.items_list, self.items[i]))
            [i.start() for i in threads]
            [i.join() for i in threads]
            self.list = sorted(self.list, key=lambda k: k['channel'])
            movies.movies().movieDirectory(self.list)
            return self.list
        except Exception:
            return self.list


