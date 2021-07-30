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
        }

        return self._session.get('/bucket', params=params).json()['page']

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
        source = data['data']['airing']['source']

        if not source['url']:
            raise APIError(_.NO_SOURCE)

        if source['authorizationType'] == 'SHIELD':
            if not self._provider.logged_in:
                raise APIError(_.NOT_ENTITLED)

            provider_data = self._provider.token(data['data']['airing']['adobeRSS'])

            payload = {
                'adobeToken': provider_data['serializedToken'],
                'adobeResource': base64.b64encode(provider_data['resource'].encode('utf8')),
                'plt': 'androidtv',
                'drmSupport': 'HLS', #DASH_WIDEVINE
            }

            data = self._session.post(source['url'], params={'apikey': SHIELD_API_KEY}, data=payload).json()
            check_errors(data)

            return {'url': data['stream']}

        elif source['authorizationType'] == 'BAM':
            if not self._espn.logged_in:
                raise APIError(_.NOT_ENTITLED)

            return self._espn.playback(source['url'])
        else:
            raise Exception('unknown auth type!')

    def logout(self):
        self._espn.logout()
        self._provider.logout()
