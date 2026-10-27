# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
# Copyright (C) 2012 Christopher Eby <kreed@kreed.org>
#This program is free software: you can redistribute it and/or modify it
#under the terms of the GNU General Public License version 3, as published
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but
#WITHOUT ANY WARRANTY; without even the implied warranties of
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

from .blowfish import Blowfish
from xml.dom import minidom
import re
import socket
import json
import logging
import time
import urllib.parse
import urllib.request
import urllib.error
import codecs
#import ssl

import xbmc # for extra logging -- may remove later

# uncomment to write a pithos.log file
#logging.basicConfig(filename='~/.kodi/temp/pithos.log',level=logging.DEBUG)

#ssl._create_default_https_context = ssl._create_unverified_context

# This is an implementation of the Pandora JSON API using Android partner
# credentials.
# See http://pan-do-ra-api.wikia.com/wiki/Json/5 for API documentation.

HTTP_TIMEOUT = 30
USER_AGENT = 'pithos'
PLAYLIST_VALIDITY_TIME = 60*60*3
NAME_COMPARE_REGEX = re.compile(r'[^A-Za-z0-9]')

API_ERROR_API_VERSION_NOT_SUPPORTED = 11
API_ERROR_COUNTRY_NOT_SUPPORTED = 12
API_ERROR_INSUFFICIENT_CONNECTIVITY = 13
API_ERROR_READ_ONLY_MODE = 1000
API_ERROR_INVALID_AUTH_TOKEN = 1001
API_ERROR_INVALID_LOGIN = 1002
API_ERROR_LISTENER_NOT_AUTHORIZED = 1003
API_ERROR_PARTNER_NOT_AUTHORIZED = 1010
API_ERROR_PLAYLIST_EXCEEDED = 1039

class PithosError(IOError):
    def __init__(self, message, status=None, submsg=None):
        self.status = status
        self.message = message
        self.submsg = submsg

class PithosAuthTokenInvalid(PithosError): pass
class PithosNetError(PithosError): pass
class PithosAPIVersionError(PithosError): pass
class PithosTimeout(PithosNetError): pass

_client = {
    'false' : {
        'deviceModel': 'android-generic',
        'username': 'android',
        'password': 'AC7IBG09A3DTSYM4R41UJWL07VLN8JI7',
        'rpcUrl': '://tuner.pandora.com/services/json/?',
        'encryptKey': '6#26FRL$ZWD',
        'decryptKey': 'R=U!LH$O2B#',
        'version' : '5',
    },
    'true' : {
        'deviceModel': 'D01',
        'username': 'pandora one',
        'password': 'TVCKIBGS9AO9TSYLNNFUML0743LH82D',
        'rpcUrl': '://internal-tuner.pandora.com/services/json/?',
        'encryptKey': '2%3WCL*JU$MP]4',
        'decryptKey': 'U#IO$RZPAB%VX2',
        'version' : '5',
    }
}


def xbmc_log(msg, level):
    prefix = '[Pandoki::pithos] '
    return xbmc.log(msg=prefix + msg, level=level)

class Pithos(object):
    def __init__(self):
        self.opener = urllib.request.build_opener()
        self.stations = []
        self.sni = False


    def pad(self, s, l):
        return s + '\0' * (l - len(s))


    def pandora_encrypt(self, s):
        def encode_hex(plain):
            return codecs.encode(plain.encode('latin-1'), 'hex').decode()

        # contains username/password.  Do not log
        #xbmc_log(msg='type(s): %s pandora_encrypt s: %s' % (type(s), s), level=xbmc.LOGDEBUG)
        return "".join([encode_hex(self.blowfish_encode.encrypt(self.pad(s[i:i+8], 8))) for i in range(0, len(s), 8)])


    def pandora_decrypt(self, s):
        def decode_hex(h):
            return "".join([chr(int(h[i:i+2], 16)) for i in range(0, len(h), 2)])

        xbmc_log(msg='type(s): %s pandora_decrypt s: %s' % (type(s), s), level=xbmc.LOGDEBUG)
        return "".join([self.blowfish_decode.decrypt(self.pad(decode_hex(s[i:i+16]), 8)) for i in range(0, len(s), 16)]).rstrip('\x08')


    def json_call(self, method, args={}, https=False, blowfish=True):
        # HEADERS = {'User-agent': USER_AGENT, 'Content-type': 'text/plain; charset=utf-8'}
        HEADERS = {'User-agent': USER_AGENT, 'Content-type': 'text/plain'}

        url_arg_strings = []
        if self.partnerId:
            url_arg_strings.append('partner_id=%s'%self.partnerId)
        if self.userId:
            url_arg_strings.append('user_id=%s'%self.userId)
        if self.userAuthToken:
            url_arg_strings.append('auth_token=%s'%urllib.parse.quote_plus(self.userAuthToken))
        elif self.partnerAuthToken:
            url_arg_strings.append('auth_token=%s'%urllib.parse.quote_plus(self.partnerAuthToken))

        url_arg_strings.append('method=%s'%method)
        protocol = 'https' if https else 'http'
        url = protocol + self.rpcUrl + '&'.join(url_arg_strings)

        xbmc_log(msg='url: %s' % url, level=xbmc.LOGDEBUG)

        if self.time_offset:
            args['syncTime'] = int(time.time()+self.time_offset)
        if self.userAuthToken:
            args['userAuthToken'] = self.userAuthToken
        elif self.partnerAuthToken:
            args['partnerAuthToken'] = self.partnerAuthToken

        data = json.dumps(args)

        if blowfish:
            data = self.pandora_encrypt(data)

        # if not self.sni:
        #     data = data.encode()
        data = data.encode()

        logging.debug(url)
        logging.debug(data)

        if self.sni:
            try:
                xbmc_log(msg='urllib3: SNI POST data: %s\ttype: %s' % (data, type(data)), level=xbmc.LOGDEBUG)
                response = self.opener.urlopen('POST', url=url, headers=HEADERS, body=data,
                                               timeout=HTTP_TIMEOUT, retries=False)
                text = response.data
                xbmc_log(msg='urllib3: SNI response: %s' % text, level=xbmc.LOGDEBUG)
            except Exception as e:
                logging.error("urllib3 Error: %s" % e)
                xbmc_log(msg='urllib3 Error: %s' % e, level=xbmc.LOGERROR)
                raise PithosNetError('urllib3 error: %s' % e)
        else:
            try:
                xbmc_log(msg='urllib: POST data: %s\ttype: %s' % (data, type(data)), level=xbmc.LOGDEBUG)
                req = urllib.request.Request(url=url, data=data, headers=HEADERS)
                response = self.opener.open(req, timeout=HTTP_TIMEOUT)
                try:
                    text = response.read().decode()
                finally:
                    response.close()
                xbmc_log(msg='urllib: response: %s' % text, level=xbmc.LOGDEBUG)
            except urllib.error.HTTPError as e:
                logging.error('urllib HTTP error: %s', e)
                xbmc_log(msg='urllib HTTP error: %s' % e, level=xbmc.LOGERROR)
                raise PithosNetError(str(e))
            except urllib.error.URLError as e:
                logging.error('urllib Network error: %s', e)
                xbmc_log(msg='urllib Network error: %s' % e, level=xbmc.LOGERROR)
                if isinstance(e.reason, (socket.timeout, TimeoutError)):
                    raise PithosTimeout('Network error', submsg='Timeout')
                raise PithosNetError('Network error', submsg=str(e.reason))
            except (socket.timeout, TimeoutError):
                raise PithosTimeout('Network error', submsg='Timeout')

        logging.debug(text)

        tree = json.loads(text)

        if tree['stat'] == 'fail':
            code = tree['code']
            msg = tree['message']
            logging.error('fault code: ' + str(code) + ' message: ' + msg)

            if code == API_ERROR_INVALID_AUTH_TOKEN:
                raise PithosAuthTokenInvalid(msg)
            elif code == API_ERROR_COUNTRY_NOT_SUPPORTED:
                 raise PithosError("Pandora not available", code,
                    submsg="Pandora is not available outside the United States.")
            elif code == API_ERROR_API_VERSION_NOT_SUPPORTED:
                raise PithosAPIVersionError(msg)
            elif code == API_ERROR_INSUFFICIENT_CONNECTIVITY:
                raise PithosError("Out of sync", code,
                    submsg="Correct your system's clock. If the problem persists, a Pithos update may be required")
            elif code == API_ERROR_READ_ONLY_MODE:
                raise PithosError("Pandora maintenance", code,
                    submsg="Pandora is in read-only mode as it is performing maintenance. Try again later.")
            elif code == API_ERROR_INVALID_LOGIN:
                raise PithosError("Login Error", code, submsg="Invalid username or password")
            elif code == API_ERROR_LISTENER_NOT_AUTHORIZED:
                raise PithosError("Pandora Error", code,
                    submsg="A Pandora One account is required to access this feature. Uncheck 'Pandora One' in Settings.")
            elif code == API_ERROR_PARTNER_NOT_AUTHORIZED:
                raise PithosError("Login Error", code,
                    submsg="Invalid Pandora partner keys. A Pithos update may be required.")
            elif code == API_ERROR_PLAYLIST_EXCEEDED:
                raise PithosError("Playlist Error", code,
                    submsg="You have requested too many playlists. Try again later.")
            else:
                raise PithosError("Pandora returned an error", code, "%s (code %d)"%(msg, code))

        if 'result' in tree:
            return tree['result']


    def set_url_opener(self, opener, sni):
        self.sni = sni
        self.opener = opener


    def connect(self, one, user, password):
        self.partnerId = self.userId = self.partnerAuthToken = None
        self.userAuthToken = self.time_offset = None

        client = _client[one]
        self.rpcUrl = client['rpcUrl']
        self.blowfish_encode = Blowfish(client['encryptKey'])
        self.blowfish_decode = Blowfish(client['decryptKey'])

        partner = self.json_call('auth.partnerLogin', {
            'deviceModel': client['deviceModel'],
            'username': client['username'], # partner username
            'password': client['password'], # partner password
            'version': client['version']
            },https=True, blowfish=False)

        self.partnerId = partner['partnerId']
        self.partnerAuthToken = partner['partnerAuthToken']

        pandora_time = int(self.pandora_decrypt(partner['syncTime'])[4:14])
        self.time_offset = pandora_time - time.time()
        xbmc_log(msg='pandora_time: %s\ttime.time(): %s' % (pandora_time, time.time()), level=xbmc.LOGDEBUG)
        xbmc_log(msg='Time offset is %s' % self.time_offset, level=xbmc.LOGDEBUG)
        logging.info("Time offset is %s", self.time_offset)

        user = self.json_call('auth.userLogin', {'username': user, 'password': password, 'loginType': 'user'}, https=True)
        self.userId = user['userId']
        self.userAuthToken = user['userAuthToken']


    def get_stations(self, *ignore):
        self.stations = []

        for s in self.json_call('user.getStationList', { 'includeStationArtUrl' : True })['stations']:
            self.stations.append({ 'id' : s['stationId'], 'token' : s['stationToken'], 'title' : s['stationName'], 'art' : s.get('artUrl') })
        logging.info('get_stations JSON: %s' % s)
        return self.stations


    def get_playlist(self, token, q = 2):
        quality = [ 'lowQuality', 'mediumQuality', 'highQuality' ]
        self.playlist = []

        for s in self.json_call('station.getPlaylist', {
                     'stationToken': token,
                     'includeTrackLength' : True,
                     'additionalAudioUrl': 'HTTP_32_AACPLUS,HTTP_128_MP3'
                      }, https = True)['items']:
            if s.get('adToken'): continue

            song = { 'id' : s['songIdentity'], 'token' : s['trackToken'], 'station' : s['stationId'], 'duration' : s.get('trackLength'),
                 'artist' : s['artistName'],   'album' : s['albumName'],    'title' : s['songName'],       'art' : s['albumArtUrl'],
                 'url' : None, 'bitrate' : 64, 'encoding' : None, 'rating' : '0' }

            logging.info('get_playlist JSON: %s' % s)
            logging.debug("####### audioUrlMap=%s additionalAudioUrl=%s" % (s['audioUrlMap'], s.get('additionalAudioUrl')))

            while q < 3:
                if s['audioUrlMap'].get(quality[q]):
                    song['url']      =     s['audioUrlMap'][quality[q]]['audioUrl']
                    song['encoding'] =     s['audioUrlMap'][quality[q]]['encoding']
                    song['bitrate']  = int(s['audioUrlMap'][quality[q]]['bitrate'])
                    break
                q += 1

            # determine if we can use 128K bit rate
            if (q == 2) and (len(s.get('additionalAudioUrl', [])) == 2):
                if int(song['bitrate']) < 128:
                    # We can use the higher quality mp3 stream for non-one users
                    song['encoding'] = 'mp3'
                    song['bitrate'] = 128
                    song['url'] = s['additionalAudioUrl'][1]

            if s['songRating'] != 0:
                song['rating'] = '3'
                song['voted'] = 'up'

            #if song['encoding'] == 'aacplus':
            #   song['encoding'] = 'm4a'
            #   song['bitrate']  = 64
            #if song['encoding'] == 'mp3-hifi':
            #   song['encoding'] = 'mp3'
            #   song['bitrate']  = 128

            self.playlist.append(song)

        return self.playlist


    def add_feedback(self, trackToken, rating_bool):
        feedback = self.json_call('station.addFeedback', {'trackToken': trackToken, 'isPositive': rating_bool})
        return feedback['feedbackId']


    def del_feedback(self, stationToken, feedbackId):
        self.json_call('station.deleteFeedback', {'feedbackId': feedbackId, 'stationToken': stationToken})


    def set_tired(self, trackToken):
        self.json_call('user.sleepSong', {'trackToken': trackToken})


    def search(self, query, artists = False):
        results = self.json_call('music.search', {'searchText': query})
        l = []

        for d in results['songs']:
            l += [{ 'score' : d['score'], 'token' : d['musicToken'], 'artist' : d['artistName'], 'title' : d['songName'] }]

        if artists:
            for d in results['artists']:
                l += [{ 'score' : d['score'], 'token' : d['musicToken'], 'artist' : d['artistName'] }]

        return sorted(l, key=lambda i: i['score'], reverse=True)


    def create_station(self, musicToken):
        s = self.json_call('station.createStation', { 'musicToken' : musicToken })
        self.stations.insert(1, { 'id' : s['stationId'], 'token' : s['stationToken'], 'title' : s['stationName'], 'art' : s.get('artUrl') })

        return self.stations[1]


    def branch_station(self, trackToken):
        s = self.json_call('station.createStation', { 'trackToken' : trackToken, 'musicType' : 'song' })
        self.stations.insert(1, { 'id' : s['stationId'], 'token' : s['stationToken'], 'title' : s['stationName'], 'art' : s.get('artUrl') })

        return self.stations[1]


    def rename_station(self, stationToken, stationName):
        for s in self.stations:
            if stationToken == s['token']:
                self.json_call('station.renameStation', { 'stationToken' : stationToken, 'stationName' : stationName })
                s['title'] = stationName

                return s
        return None


    def delete_station(self, stationToken):
        for s in self.stations:
            if stationToken == s['token']:
                self.json_call('station.deleteStation', { 'stationToken' : stationToken })
                self.stations.remove(s)

                return s
        return None


    def seed_station(self, stationToken, musicToken):
        for s in self.stations:
            if stationToken == s['token']:
                self.json_call('station.addMusic', { 'stationToken' : stationToken, 'musicToken' : musicToken} )

                return s
        return None
