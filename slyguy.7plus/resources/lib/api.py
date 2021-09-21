from time import time

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data, process_brightcove
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS)

    @mem_cache.cached(60*5)
    def _market_id(self):
        try:
            return self._session.get('https://market-cdn.swm.digital/v1/market/ip/', params={'apikey': 'web'}).json()['_id']
        except:
            log.debug('Failed to get market id')
            return '4' #Sydney

    def nav(self):
        params = {
            'platform-id': 'web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': '4.3',
        }

        return self._session.get('https://component-cdn.swm.digital/content/nav', params=params).json()['items']

    def search(self, query):
        params = {
            'searchTerm': query,
            'market-id': self._market_id(),
            'api-version': '4.4',
            'platform-id': 'androidtv',
            'platform-version': '4.25',
        }

        return self._session.get('https://searchapi.swm.digital/3.0/api/Search', params=params).json()

    def content(self, slug):
        params = {
            'platform-id': 'androidtv',
            'market-id': self._market_id(),
            'platform-version': '4.25',
            'api-version': '4.4',
        }

        return self._session.get('https://component-cdn.swm.digital/content/{slug}'.format(slug=slug), params=params).json()

    def component(self, slug, component_id):
        params = {
            'component-id': component_id,
            'platform-id': 'AndroidTv',
            'market-id': self._market_id(),
            'platform-version': '4.25.0.0',
            'api-version': '4.4.0.0',
            'signedUp': 'True',
        }

        return self._session.get('https://component.swm.digital/component/{slug}'.format(slug=slug), params=params).json()

    def video_player(self, slug):
        params = {
            'platform-id': 'AndroidTv',
            'market-id': self._market_id(),
            'platform-version': '4.25.0.0',
            'api-version': '4.4.0.0',
            'signedUp': 'True',
        }

        return self._session.get('https://component.swm.digital/player/live/{slug}'.format(slug=slug), params=params).json()['videoPlayer']

    def play(self, account, reference, live):
        params = {
            'appId': '7plus',
            'platformType': 'tv',
            'accountId': account,
            'referenceId': reference,
            'deliveryId': 'csai',
            'advertid': 'null',
            'deviceId': 'fm-k_zfMS1it5axvWRqkRt',
            'pc': 3350,
            'deviceType': 'androidtv',
            'ozid': 'b09f7dc3-3999-47c7-a09f-8dce404c0455',
            'sdkverification': 'true',
        }

        if live:
            params['videoType'] = 'live'

        data = self._session.get('https://videoservice.swm.digital/playback', params=params).json()
        if 'media' not in data:
            raise APIError(data[0]['error_code'])

        return process_brightcove(data['media'])
