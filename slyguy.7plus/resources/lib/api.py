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
            return self._session.get(MARKET_ID_URL, params={'apikey': 'web'}).json()['_id']
        except:
            log.debug('Failed to get market id')
            return '4' #Sydney

    def search(self, query):
        params = {
            'searchTerm': query,
            'market-id': self._market_id(),
            'platform-id': 'Web',
            'size': 30,
        }

        return self._session.get('https://searchapi.swm.digital/3.0/api/Search', params=params).json()

    def content(self, slug):
        params = {
            'platform-id': 'web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': '4.3',
        }

        return self._session.get('https://component-cdn.swm.digital/content/{slug}'.format(slug=slug), params=params).json()

    def component(self, slug, component_id):
        params = {
            'platform-id': 'Web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': '4.3.0.0',
            'component-id': component_id,
        }

        return self._session.get('https://component.swm.digital/component/{slug}'.format(slug=slug), params=params).json()

    def video_player(self, slug):
        params = {
            'platform-id': 'Web',
            'market-id': self._market_id(),
            'api-version': '4.3.0.0',
            'signedUp': 'True',
            'platform-version': '1.0.67393',
        }

        return self._session.get('https://component.swm.digital/player/live/{slug}'.format(slug=slug), params=params).json()['videoPlayer']

    def play(self, account, reference, live):
        params = {
            'appId': '7plus',
            'deviceType': 'web',
            'platformType': 'web',
            'ppId': '',
            'deviceId': '63d5f1ba-4e6c-4f50-9b5f-d624cf907f55',
            'pc': 1000,
            'advertid': 'null',
            'accountId': account,
            'referenceId': reference,
            'deliveryId': 'csai',
            'tvid': 'null',
            'ozid': '7bd7ba65-f070-4164-9266-8ce94d25acb3',
        }

        if live:
            params['videoType'] = 'live'

        headers = {
            'X-USE-AUTHENTICATION': 'UseTokenAuthentication',
            'authorization': 'Bearer {}'.format(DEFAULT_TOKEN),
        }

        data = self._session.get('https://videoservice.swm.digital/playback', params=params, headers=headers).json()
        if 'media' not in data:
            raise APIError(data[0]['error_code'])

        return process_brightcove(data['media'])
