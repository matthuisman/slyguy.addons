import json
import base64

from slyguy.session import Session
from slyguy.exceptions import Error

from . import queries
from .espn import ESPN
from .provider import Provider
from .util import check_errors
from .language import _

HEADERS = {
    'User-Agent': 'ESPN/4.7.1 Dalvik/2.1.0 (Linux; U; Android 8.1.0; MI 5 Build/OPM7.181005.003)',
    'always-ok-response': 'true',
}

API_URL = 'https://watch.product.api.espn.com/api/product/v3/android/tv{}'
WATCH_URL = 'https://watch.graph.api.espn.com/api'
WATCH_KEY = '37e46a0e-505b-430a-b5f0-3d332266c1a9'
SHIELD_API_KEY = 'uiqlbgzdwuru14v627vdusswb'

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._session = Session(HEADERS, base_url=API_URL, timeout=30)
        # self._session.headers.update({
        #     'dss-session-token': '123'
        # })
        self._espn = ESPN()
        self._provider = Provider()
        self.logged_in = self._espn.logged_in or self._provider.logged_in

    @property
    def espn(self):
        return self._espn

    @property
    def provider(self):
        return self._provider

    def bucket(self, bucket_id):
        params = {
            'bucketId': bucket_id,
            'authNetworks': 'espn1,espn2,espnu,espnews,espndeportes,sec,longhorn,buzzerbeater,goalline,espn3,espnclassic,acc,accextra,espnvod,secplus',
            'authStates': 'mvpd_login',
            'entitlements': 'ESPN_PLUS',
        }
        return self._session.get('/bucket', params=params).json()['page']

    def event(self, event_id):
        params = {
            'eventId': event_id,
        }
        return self._session.get('/event', params=params).json()['page']['contents']

    def picker(self, event_id):
        params = {
            'eventId': event_id,
            'partitionDtc': 'true',
            'tz': 'UTC',
            # 'countryCode': 'US',
            # 'lang': 'en',
            # 'deviceType': 'settop',
            # 'entitlements': 'ESPN_PLUS',
            # 'appVersion': '4.7.1',
            # 'iapPackages': 'ESPN_PLUS_UFC_PPV_265,ESPN_PLUS',
            # 'features': 'imageRatio58x13,promoTiles,openAuthz',
        }
        return self._session.get('/picker', params=params).json()['page'].get('buckets', [])

    def play_network(self, network):
        params = {
            'network': network,
        }
        return self._session.get('/playback/event', params=params).json()['playbackState']

    def play(self, content_id):
        variables = {
            'countryCode': 'US',
            'deviceType': 'SETTOP',
            'tz': 'UTC',
            'id': content_id,
        }

        params = {
            'apiKey': WATCH_KEY,
            'query': queries.WATCH,
            'variables': json.dumps(variables),
        }

        data = self._session.get(WATCH_URL, params=params).json()
        airing = data['data']['airing']
        source = airing['source']

        if not source['url']:
            raise APIError(_.NO_SOURCE)

        if source['authorizationType'] == 'SHIELD':
            if not self._provider.logged_in:
                raise APIError(_.NOT_ENTITLED)

            provider_data = self._provider.token(airing['adobeRSS'])

            payload = {
                'adobeToken': provider_data['serializedToken'],
                'adobeResource': base64.b64encode(provider_data['resource'].encode('utf8')),
                'plt': 'androidtv',
                'drmSupport': 'HLS', #DASH_WIDEVINE
            }

            data = self._session.post(source['url'], params={'apikey': SHIELD_API_KEY}, data=payload).json()
            check_errors(data)

            return airing, {'url': data['stream']}

        elif source['authorizationType'] == 'BAM':
            if not self._espn.logged_in:
                raise APIError(_.NOT_ENTITLED)

            return airing, self._espn.playback(source['url'])
        else:
            raise Exception('unknown auth type!')

    def logout(self):
        self._espn.logout()
        self._provider.logout()
