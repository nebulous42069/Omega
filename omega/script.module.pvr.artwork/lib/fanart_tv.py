from .tools import *


class FanartTv(object):

    def __init__(self):
        self.api_key = ADDON.getSetting('fanart_apikey')

        self.endpoint = dict({'movie': 'movies', 'tvshow': 'tv'})
        self.prefix = dict({'movie': 'movie', 'tvshow': 'tv'})

        self.arttypes = dict({'fanart': 'fanart', 'thumb': 'thumb', 'banner': 'banner', 'logo': 'logo',
                              'background': 'fanart', 'landscape': 'landscape', 'poster': 'poster'})

        self.arttypes_general = dict({'disc': 'discart', 'clearlogo': 'clearlogo', 'clearart': 'clearart',
                                      'characterart': 'characterart'})

    def get_fanart_data(self, endpoint, params):
        """
            helper method to get data from fanart.tv json API
        """
        url = u'http://webservice.fanart.tv/v3/%s/%s' % (endpoint, params['id'])

        if self.api_key:
            params.update({'api_key': self.api_key})

        params.pop('id')
        return get_json(url, params, prefix=None)

    def get_localized_art(self, artwork, group, key, fanart):
        for index, item in enumerate(fanart):
            if item.get('lang') == LANGUAGE:
                log('Found %s in preferred language \'%s\'' % (key, LANGUAGE))
                return artwork.update({group[key]: item.get('url')})

        # no preferred fanart found, simply return with first item
        return artwork.update({group[key]: fanart[0].get('url')})

    def get_fanarts(self, media_type, media_id):

        if not (media_type and media_id): return False

        params = dict({'id': media_id, 'lang': LANGUAGE})
        res = self.get_fanart_data(self.endpoint[media_type], params)

        if res is None or res.get('status') == 'error': return False

        artwork = dict()
        for fanart in res:
            for key in self.arttypes:
                if '%s%s' % (self.prefix[media_type], key) in fanart: self.get_localized_art(artwork, self.arttypes,
                                                                                             key, res[fanart])

            # get general fanarts
            for key in self.arttypes_general:
                if key in fanart: self.get_localized_art(artwork, self.arttypes_general, key, res[fanart])

        return artwork
