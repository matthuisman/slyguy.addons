import uuid
from time import time

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            return

        self._session.headers.update({'authorization': access_token})
        self.logged_in = True

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time() or not self.logged_in:
            return

        log.debug('Refreshing token')

        data = self._session.get(API_URL+'identity/refresh/{}'.format(userdata.get('refresh_token'))).json()
        self._process_token(data)

    def _process_token(self, data):
        if 'error' in data:
            raise APIError(data['error'])

        userdata.set('access_token', data['authorizationToken'])
        if 'refreshToken' in data:
            userdata.set('refresh_token', data['refreshToken'])

        token_data = jwt_data(data['authorizationToken'])
        userdata.set('expires', int(time()+(token_data['exp']-token_data['iat']-30)))

        self._set_authentication()

    def login(self, username, password):
        self.logout()

        deviceid = str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), str(username.lower().strip())))

        params = {
            'site': 'live-rugby',
            'deviceId': 'browser-{}'.format(deviceid),
        }

        payload = {
            'email': username,
            'password': password,
        }

        data = self._session.post(API_URL+'identity/signin', json=payload, params=params).json()
        self._process_token(data)

    @mem_cache.cached(60*5)
    def page(self, slug):
        params = {
            'site': 'live-rugby',
            'path': slug,
            'includeContent': 'true',
            #'moduleOffset': 0,
            #'moduleLimit': 8,
            'languageCode': 'default',
            'countryCode': 'NZ',
        }

        return self._session.get(CACHED_API_URL+'content/pages', params=params).json()

    @mem_cache.cached(60*5)
    def search(self, query):
        params = {
            'site': 'live-rugby',
            'searchTerm': query,
            'types': 'VIDEO,SERIES,EVENT',#,ARTICLE,PERSON,BUNDLE',
            'languageCode': 'default',
        }

        return self._session.get(CACHED_API_URL+'search/v1', params=params).json()

    def play(self, id):
        self._refresh_token()

        params = {
            'id': id,
            'deviceType': 'web_browser',
            'contentConsumption': 'web',
        }

        data = self._session.get(API_URL+'entitlement/video/status', params=params).json()

        if not data['success']:
            raise APIError(data['errorMessage'])

        return data['video']['streamingInfo']['videoAssets']['hls']

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        self.new_session()