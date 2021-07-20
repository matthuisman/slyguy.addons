import hashlib

from bs4 import BeautifulSoup
from slyguy import userdata, settings
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log

from .constants import *

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self._logged_in = False
        self._language  = COMM_LANG
        self._session   = Session(HEADERS, base_url=API_URL)
        self._set_access_token(userdata.get('access_token'))

    def _set_access_token(self, token):
        if token:
            self._session.headers.update({'Authorization': 'Bearer {}'.format(token)})
            self._logged_in = True

    @property
    def logged_in(self):
        return self._logged_in

    def login(self, username, password):
        self.logout()

        data = {
            'response_type': 'token',
            'lang': self._language,
        }

        resp = self._session.get(LOGIN_URL, params=data)

        soup = BeautifulSoup(resp.text, 'html.parser')
        for form in soup.find_all('form'):
            data = {}

            for e in form.find_all('input'):
                data[e.attrs['name']] = e.attrs.get('value')

            if 'signin[email]' in data:
                break

        data.update({
            'signin[email]': username,
            'signin[password]': password,
        })

        resp = self._session.post(LOGIN_URL, data=data, allow_redirects=False)
        access_token = resp.cookies.get('showmax_oauth')

        if not access_token:
            raise APIError('Failed to login')

        self._set_access_token(access_token)

        data = self._session.get('user/current', params={'lang': self._language}).json()
        if 'error_code' in data:
            raise APIError('Failed to login')

        device_id = hashlib.sha1(username.lower().strip().encode('utf8')).hexdigest().upper()

        userdata.set('device_id', device_id)
        userdata.set('access_token', access_token)
        userdata.set('user_id', data['user_id'])

    def logout(self):
        userdata.delete('device_id')
        userdata.delete('access_token')
        userdata.delete('user_id')
        self.new_session()

    def _catalogue(self, _params):
        def process_page(start):
            params = {
                'field[]': ['id'],
                'lang': self._language,
                'showmax_rating': '18-plus',
                'sort': 'alphabet',
                'start': start,
                'subscription_status': 'full',
                'mode': 'paid',
               # 'content_country': 'ZA',
            }

            params.update(_params)

            data = self._session.get('catalogue/assets', params=params).json()
            items = data['items']

            count     = int(data.get('count', 0))
            remaining = int(data.get('remaining', 0))
            if count > 0 and remaining > 0:
                items.extend(process_page(start + count))

            return items

        return process_page(start=0)

    def series(self):
        return self._catalogue({
            'field[]': ['id', 'images', 'title', 'items', 'total', 'description', 'videos', 'type'],
            'type': 'tv_series',
        })

    def movies(self):
        return self._catalogue({
            'field[]': ['id', 'images', 'title', 'items', 'total', 'description', 'videos', 'type'],
            'type': 'movie',
        })

    def kids(self):
        return self._catalogue({
            'field[]': ['id', 'images', 'title', 'items', 'total', 'description', 'videos', 'type'],
            'showmax_rating': '5-6',
            'types[]': ['tv_series', 'movie'],
        })

    def seasons(self, series_id):
        params = {
            'field[]': ['id', 'images', 'title', 'items', 'total', 'description', 'number', 'seasons', 'type'],
            'lang': self._language,
            'showmax_rating': '18-plus',
            'subscription_status': 'full',
        }

        return self._session.get('catalogue/tv_series/{}'.format(series_id), params=params).json()

    def episodes(self, season_id):
        params = {
            'field[]': ['id', 'images', 'title', 'items', 'total', 'description', 'number', 'tv_series', 'episodes', 'videos', 'type'],
            'lang': self._language,
            'showmax_rating': '18-plus',
            'subscription_status': 'full',
        }

        return self._session.get('catalogue/season/{}'.format(season_id), params=params).json()

    def search(self, query):
        return self._catalogue({
            'field[]': ['id', 'images', 'title', 'items', 'total', 'type', 'description', 'type', 'videos'],
            'types[]': ['tv_series', 'movie'],
            'showmax_rating': '18-plus',
            'subscription_status': 'full',
            'q': query,
        })

    def asset(self, asset_id):
        params = {
            'field[]': ['videos',],
            'exclude[]': 'episodes',
            'lang': self._language,
            'showmax_rating': '18-plus',
            'subscription_status': 'full',
        }

        return self._session.get('catalogue/asset/{}'.format(asset_id), params=params).json()['videos']

    def play(self, video_id):
        codecs = ''

        if settings.getBool('vp9', False):
            codecs += 'vp9+'
        if settings.getBool('h265', False):
            codecs += 'hevc+'
        if settings.getBool('h264', True):
            codecs += 'h264+'

        codecs = codecs.rstrip('+')

        params = {
            'capabilities[]': ['codecs={}'.format(codecs), 'multiaudio'],
            'encoding': 'mpd_widevine_modular',
            'subscription_status': 'full',
            'mode': 'paid',
            'showmax_rating': '18-plus',
            'lang': self._language,
         #   'content_country': 'ZA',
        }

        data = self._session.get('playback/play/{}'.format(video_id), params=params).json()
        if 'url' not in data:
            raise APIError(data.get('message'))

        url        = data['url']
        task_id    = data['packaging_task_id']
        session_id = data['session_id']

        data = {
            'user_id': userdata.get('user_id'),
            'video_id': video_id,
            'hw_code': userdata.get('device_id'),
            'packaging_task_id': task_id,
            'session_id': session_id,
        }

        params = {
            'showmax_rating': '18-plus',
            'mode': 'paid',
            'subscription_status': 'full',
            'lang': self._language,
        }

        data = self._session.post('playback/verify', params=params, data=data).json()

        if 'license_request' not in data:
            raise APIError(data.get('message'))

        license_request = data['license_request']
        license_url = API_URL.format('drm/widevine_modular?license_request={}'.format(license_request))

        return url, license_url