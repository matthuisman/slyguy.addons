import time

from slyguy import userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from .language import _
from .constants import *

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        auth_token = userdata.get('auth_token')
        if not auth_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(auth_token)})
        self.logged_in = True

    def device_code(self):
        return self._session.get('/v2/token/alt/pin').json()

    def device_login(self, pin, anchor):
        self.logout()

        payload = {
            'pin': pin,
            'anchor': anchor,
        }

        data = self._session.post('/v2/token/alt/pin', json=payload).json()
        return self._parse_auth(data)

    def login(self, username, password):
        self.logout()
        
        payload = {
            'id': username,
            'secret': password,
        }

        data = self._session.post('/v2/login', json=payload).json()
        if not self._parse_auth(data):
            raise APIError(_.LOGIN_ERROR)

    def _parse_auth(self, data):
        if not data.get('authorisationToken'):
            return False

        auth_token = data['authorisationToken']
        jwt = jwt_data(auth_token)

        userdata.set('auth_token', auth_token)
        userdata.set('token_expires', int(time.time()) + (jwt['exp'] - jwt['iat'] - 30))
        if 'refreshToken' in data:
            userdata.set('refresh_token', data['refreshToken'])

        self._set_authentication()
        return True

    def _refresh_token(self):
        if userdata.get('token_expires', 0) > time.time():
            return

        log.debug('Refreshing token')

        payload = {
            'refreshToken': userdata.get('refresh_token'),
        }

        data = self._session.post('/v2/token/refresh', json=payload).json()
        self._parse_auth(data)

    def channels(self):
        self._refresh_token()
        params = {'rpp': 25}
        data = self._session.get('/v2/event/live', params=params).json()
        return data['events']

    def play(self, event_id):
        self._refresh_token()

        params = {
            'displayGeoblockedLive': True,
        }
        event_data = self._session.get('/v2/event/{}'.format(event_id), params=params).json()

        params = {
            'eventId': event_id,
            'sportId': 0,
            'propertyId': 0,
            'tournamentId': 0,
            'displayGeoblockedLive': True,
        }
        stream_data = self._session.get('/v2/stream'.format(event_id), params=params).json()
        playback_data = self._session.get(stream_data['playerUrlCallback']).json()
        return playback_data, event_data

    def logout(self):
        userdata.delete('auth_token')
        userdata.delete('refresh_token')
        userdata.delete('token_expires')
        self.new_session()
