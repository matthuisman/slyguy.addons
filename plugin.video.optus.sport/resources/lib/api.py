import time

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from .constants import HEADERS, API_URL, AWS_URL, AWS_CLIENT_ID
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        id_token = userdata.get('id_token')
        if not id_token:
            return

        self._session.headers.update({'Authorization': id_token})
        self.logged_in = True

    def navigation(self):
        return self._session.get('/metadata/navigations/nav_v1').json()['navigations']

    def page(self, name):
        data = self._session.get('/metadata/pages/{}'.format(name)).json()
        return [x for x in data['panels'] if 'title' in x]

    def editorial(self, name):
        data = self._session.get('/metadata/editorials/v2/{}/mobile'.format(name)).json()
        return data['assets']

    def asset(self, id):
        return self._session.get('/metadata/assets/v2/{}/mobile'.format(id)).json()

    def login(self, username, password):
        self.logout()

        payload = {
            "username": username,
            "password": password,
            "rememberMe": "false"
        }

        r = self._session.post('/userauth/login', json=payload)

        if not r.ok:
            if r.status_code == 403:
                 raise APIError(_.GEO_BLOCKED)
            else:
                raise APIError(_(_.LOGIN_ERROR, msg=r.json()['error'].get('description')))

        data = r.json()
        userdata.set('user_id', data['userId'])
        self._parse_token(data['result'])

    def _parse_token(self, data):
        userdata.set('id_token', data['IdToken'])
        userdata.set('expires', int(time.time() + data['ExpiresIn'] - 15))

        if 'RefreshToken' in data:
            userdata.set('refresh_token', data['RefreshToken'])

        self._set_authentication()

    def _check_token(self):
        if userdata.get('expires') > time.time():
            return

        headers = {
            'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
            'X-Amz-User-Agent': 'aws-amplify/0.1.x js',
            'Content-Type': 'application/x-amz-json-1.1',
        }

        payload = {
            'AuthFlow': 'REFRESH_TOKEN_AUTH',
            'AuthParameters': {
                'DEVICE_KEY': None,
                'REFRESH_TOKEN': userdata.get('refresh_token'),
            },
            'ClientId': AWS_CLIENT_ID,
        }

        r = self._session.post(AWS_URL, json=payload, headers=headers)
        data = r.json()
        if 'message' in data:
            raise APIError(_(_.LOGIN_ERROR, msg=data['message']))

        self._parse_token(data['AuthenticationResult'])

    def play(self, asset, from_start=False):
        self._check_token()

        params = {
            'type': 'dash',
            'drm': 'widevine',
            'yspSdk': 'true',
            'watchMode': 'startover' if from_start else 'live',
        }

        r = self._session.get('/playback/generalPlayback/web/users/{user_id}/assets/{asset_id}'.format(user_id=userdata.get('user_id'), asset_id=asset), params=params)

        if not r.ok:
            if r.status_code == 403:
                raise APIError(_.GEO_BLOCKED)
            else:
                raise APIError(r.json()['error'].get('description'))

        try:
            data = r.json()
            stream = data['playback']['items']['item']
            if type(stream) is list:
                stream = stream[0]
        except:
            stream = None

        if not stream:
            raise APIError(_.NO_STREAM)

        return stream

    def logout(self):
        userdata.delete('user_id')
        userdata.delete('id_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        self.new_session()