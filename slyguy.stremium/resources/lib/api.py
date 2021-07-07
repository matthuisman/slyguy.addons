from time import time

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(base_url=API_URL, headers=HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            return

        self._session.headers.update({'authorization': access_token})
        self.logged_in = True

    def _refresh_token(self, force=False):
        refresh_token = userdata.get('refresh_token')
        if not refresh_token or (not force and userdata.get('expires', 0) > time()):
            return

        params = {
            'key': GOOGLE_KEY,
        }

        payload = {
            'grantType': 'refresh_token',
            'refreshToken': refresh_token,
        }

        data = self._session.post(TOKEN_URL, params=params, json=payload).json()
        if 'error' in data:
            self.logout()
            raise APIError(data['error']['message'])

        userdata.set('access_token', data['access_token'])
        userdata.set('refresh_token', data['refresh_token'])
        userdata.set('expires', int(time()) + int(data['expires_in']) - 30)
        self._set_authentication()

    @mem_cache.cached(60*5)
    def channels(self):
        self._refresh_token()

        params = {
            'noGuideData': True,
        }

        return self._session.get('/programGuide', params=params).json()

    def play(self, id):
        self._refresh_token()

        params = {
            'channelId': id,
        }

        return self._session.get('/playbackAuthenticated', params=params).json()

    def epg(self):
        self._refresh_token()
        return self._session.get('/programGuide').json()

    def login(self, email, password, register=False):
        self.logout()

        params = {
            'key': GOOGLE_KEY,
        }

        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True,
        }

        data = self._session.post(REGISTER_URL if register else LOGIN_URL, params=params, json=payload).json()
        if 'error' in data:
            raise APIError(data['error']['message'])

        userdata.set('refresh_token', data['refreshToken'])
        self._refresh_token(force=True)

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        mem_cache.empty()
        self.new_session()
