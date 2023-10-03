from time import time

from slyguy import userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._auth_header = {}
        self._subscribed = None

        self._session = Session(base_url=self.BASE_URL, attempts=4, return_json=True, ssl_ciphers=SSL_CIPHERS, ssl_options=SSL_OPTIONS)
        self._session.headers = HEADERS
        self._set_authentication()

    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            return

        self._auth_header = {'Authorization': 'Bearer {}'.format(access_token)}
        self.logged_in = True

    def _oauth_token(self, data, _raise=True):
        token_data = self._session.post(AUTH_URL + '/token', json=data, error_msg=_.TOKEN_ERROR)

        if 'error' in token_data:
            error = _.REFRESH_TOKEN_ERROR if data.get('grant_type') == 'refresh_token' else _.LOGIN_ERROR
            if _raise:
                raise APIError(_(error, msg=token_data.get('error_description')))
            else:
                return False, token_data

        userdata.set('access_token', token_data['access_token'])
        userdata.set('expires', int(time() + token_data['expires_in'] - 15))

        if 'refresh_token' in token_data:
            userdata.set('refresh_token', token_data['refresh_token'])

        self._set_authentication()
        return True, token_data

    def device_code(self):
        payload = {
            'client_id': self.CLIENT_ID,
            'audience': 'streamotion.com.au',
            'scope': 'openid offline_access drm:low email',
        }

        return self._session.post(AUTH_URL + '/device/code', json=payload)

    def device_login(self, device_code):
        payload = {
            'client_id': self.CLIENT_ID,
            'device_code': device_code,
            'scope': 'openid offline_access drm:low email',
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        }

        result, token_data = self._oauth_token(payload, _raise=False)
        if result:
            self._refresh_token(force=True)
            return True

        if token_data.get('error') != 'authorization_pending':
            raise APIError(_(_.LOGIN_ERROR, msg=token_data.get('error_description')))
        else:
            return False

    def refresh_token(self):
        self._refresh_token()

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time() or not self.logged_in:
            return

        log.debug('Refreshing token')

        payload = {
            'client_id': self.CLIENT_ID,
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'openid offline_access drm:low email',
        }

        self._oauth_token(payload)

    def login(self, username, password):
        payload = {
            'client_id': self.CLIENT_ID,
            'username': username,
            'password': password,
            'audience': 'streamotion.com.au',
            'scope': 'openid offline_access drm:low email',
            'grant_type': 'http://auth0.com/oauth/grant-type/password-realm',
            'realm': 'prod-martian-database',
        }

        self._oauth_token(payload)
        self._refresh_token(force=True)

    def license_request(self, data):
        self._refresh_token()
        return self._session.post(LICENSE_URL, data=data, return_json=False, headers=self._auth_header).content

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        self.new_session()
