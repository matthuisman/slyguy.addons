from slyguy import mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import process_brightcove
from slyguy.log import log

from .constants import *
from .language import _
from .settings import settings


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS)

    def _market_id(self):
        SYDNEY_MARKET_ID = 4

        @mem_cache.cached(60*10)
        def auto():
            try:
                return self._session.get('https://market-cdn.swm.digital/v1/market/ip/', params={'apikey': 'web'}).json()['_id']
            except:
                log.debug('Failed to get market id from IP. Default to Sydney')
                return SYDNEY_MARKET_ID

        @mem_cache.cached(60*30)
        def lat_long(lat, long):
            try:
                return self._session.get('https://market-cdn.swm.digital/v1/market/location/', params={'apikey': 'web', 'lat': '{:.4f}'.format(lat), 'lon': '{:.4f}'.format(long)}).json()['_id']
            except:
                log.debug('Failed to get market id from lat long. Default to Sydney')
                return SYDNEY_MARKET_ID

        try:
            latitude, longitude = settings.get('lat_long').strip().split(',')
            market_id = lat_long(float(latitude), float(longitude))
        except:
            market_id = auto()

        log.debug('Market ID: {}'.format(market_id))
        return market_id

    def nav(self):
        params = {
            'platform-id': 'web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': API_VERSION,
        }

        return self._session.get('https://component-cdn.swm.digital/content/nav', params=params).json()['items']

    def search(self, query):
        params = {
            'searchTerm': query,
            'market-id': self._market_id(),
            'api-version': '4.4',
            'platform-id': PLATFORM_ID,
            'platform-version': PLATFORM_VERSION,
        }

        return self._session.get('https://searchapi.swm.digital/3.0/api/Search', params=params).json()

    def content(self, slug):
        params = {
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
        }

        return self._session.get('https://component-cdn.swm.digital/content/{slug}'.format(slug=slug), params=params).json()

    def component(self, slug, component_id):
        params = {
            'component-id': component_id,
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
            'signedUp': 'True',
        }

        return self._session.get('https://component.swm.digital/component/{slug}'.format(slug=slug), params=params).json()

    def video_player(self, slug):
        params = {
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
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
            'pc': 3350, #postcode
            'deviceType': PLATFORM_ID,
            'ozid': 'b09f7dc3-3999-47c7-a09f-8dce404c0455',
            'encryptionType': 'cenc',
            'drmSystems': 'widevine',
            'containerFormat': 'cmaf',
            'supportedCodecs': 'avc',
            'sdkverification': 'true',
        }

        if live:
            params['videoType'] = 'live'

        headers = {
            'X-USE-AUTHENTICATION': 'UseTokenAuthentication',
            'Authorization': 'Bearer {}'.format(DEFAULT_TOKEN),
        }

        data = self._session.get('https://videoservice.swm.digital/playback', params=params, headers=headers).json()
        if 'media' not in data:
            raise APIError(data[0]['error_code'])

        item = process_brightcove(data['media'])
        return item
