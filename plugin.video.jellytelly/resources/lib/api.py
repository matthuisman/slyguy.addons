import hashlib

from slyguy import userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log

from .constants import HEADERS, API_URL
from .language import _
from .settings import settings


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session  = Session(HEADERS, base_url=API_URL)
        self._set_authentication()
        
    def _set_authentication(self):
        access_token = userdata.get('token')
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Token token="{}"'.format(access_token)})
        self.logged_in = True

    def _require_auth(self):
        r = self._session.post('/watchlist', headers={'Accept': 'version=5'})
        if r.status_code == 200:
            return

        log.debug('Session expired')

        pswd = userdata.get('pswd')
        if not pswd:
            self.logout()
            raise APIError(_.SESSION_EXPIRED_DESC, heading=_.SESSION_EXPIRED)

        log.debug('Logging in with saved password')
        self.login(userdata.get('username'), pswd)

    def apps(self, key=None):
        self._require_auth()

        data = self._session.get('/logged_in_apps', headers={'Accept': 'version=4'}).json()
        if not key:
            return data

        return data.get(key)

    def add_watchlist(self, series_id):
        self._require_auth()

        params = {'series_id': series_id}
        r = self._session.post('/watchlist', params=params, headers={'Accept': 'version=5'})
        return r.status_code == 200

    def del_watchlist(self, series_id):
        self._require_auth()

        r = self._session.delete('/watchlist/{}'.format(series_id), headers={'Accept': 'version=5'})
        return r.status_code == 204

    def search(self, query):
        params = {'query': query}
        return self._session.post('/search', params=params, headers={'Accept': 'version=6'}).json()

    def series(self, series_id):
        return self._session.get('/series/{}'.format(series_id), headers={'Accept': 'version=4'}).json()

    def login(self, username, password):
        device_id = hashlib.md5(username.lower().strip().encode('utf8')).hexdigest()[:16]

        payload = {
            'email': username,
            'password': password,
            'device_type': 'android',
            'device_id': device_id,
        }

        data = self._session.post('/login', data=payload).json()
        if 'errors' in data:
            raise APIError(_(_.LOGIN_ERROR, msg=data['errors']))

        userdata.set('device_id', device_id)
        userdata.set('token', data['user_info']['auth_token'])
        userdata.set('user_id', data['user_info']['id'])

        if settings.getBool('save_password', False):
            userdata.set('pswd', password)

        self._set_authentication()

    def add_favourite(self, video_id):
        self._require_auth()

        params = {'video_id': video_id}
        r = self._session.post('/favorites', params=params, headers={'Accept': 'version=4'})
        return r.status_code == 200

    def del_favourite(self, video_id):
        self._require_auth()

        r = self._session.delete('/favorites/{}'.format(video_id), headers={'Accept': 'version=4'})
        return r.status_code == 204

    def streams(self, series_id, video_id):
        self._require_auth()

        videos = self.series(series_id)['videos']

        for video in videos:
            if str(video['id']) == str(video_id):
                return video['streams']

        return []

    def favourites(self):
        self._require_auth()

        return self._session.get('/users/{}/favorites'.format(userdata.get('user_id')), headers={'Accept': 'version=3'}).json()['favorite_videos']

    def user(self):
        self._require_auth()

        return self._session.get('/users/{}'.format(userdata.get('user_id'))).json()

    def logout(self):
        userdata.delete('token')
        userdata.delete('deviceid')
        userdata.delete('user_id')
        self.new_session()