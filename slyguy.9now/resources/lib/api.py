import time

from slyguy import util, userdata, mem_cache, log
from slyguy.util import jwt_data
from slyguy.session import Session

from .constants import *


class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication(userdata.get('access_token'))

    def _set_authentication(self, access_token):
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(access_token)})
        self.logged_in = True

    def device_code(self):
        self.logout()
        params = {
            'client_id': '9nowdevice',
        }
        return self._session.post(AUTH_URL.format('/code'), params=params, data={}).json()

    def device_login(self, auth_code, device_code):
        params = {
            'auth_code': auth_code,
            'device_code': device_code,
            'client_id': '9nowdevice',
            'response_types': 'id_token',
        }
        data = self._session.get(AUTH_URL.format('/token'), params=params).json()
        if 'accessToken' not in data:
            return False

        userdata.set('access_token', data['accessToken'])
        userdata.set('token_expires', int(time.time()) + data['expiresIn'] - 30)
        userdata.set('refresh_token', data['refresh_token'])
        return True

    def _refresh_token(self, force=False):
        if not force and userdata.get('token_expires', 0) > time.time():
            return

        log.debug('Refreshing token')

        params = {
            'refresh_token': userdata.get('refresh_token'),
            'client_id': '9nowdevice',
            'response_types': 'id_token',
        }
        data = self._session.post(AUTH_URL.format('/refresh-token'), params=params).json()
        if 'error' in data:
            raise Exception(data['error'])

        userdata.set('access_token', data['accessToken'])
        userdata.set('token_expires', int(time.time()) + data['expiresIn'] - 30)

    def featured(self):
        self._refresh_token()
        return self._session.get('/home', params={'device': 'web'}).json()

    def shows(self):
        self._refresh_token()
        return self._session.get('/tv-series', params={'device': 'web'}).json()['tvSeries']

    def show(self, show):
        self._refresh_token()
        return self._session.get('/tv-series/{show}'.format(show=show), params={'device': 'web'}).json()

    def episodes(self, show, season, page=1, items_per_page=None):
        self._refresh_token()
        params = {
            'device': 'web',
            'sort': '',
        }

        if items_per_page:
            params['take'] = items_per_page
            params['skip'] = (page-1)*items_per_page

        return self._session.get('/tv-series/{show}/seasons/{season}/episodes'.format(show=show, season=season), params=params).json()

    def clips(self, show, season, page=1, items_per_page=None):
        self._refresh_token()
        params = {
            'device': 'web',
            'sort': '',
            'tagSlug': '',
        }

        if items_per_page:
            params['take'] = items_per_page
            params['skip'] = (page-1)*items_per_page

        return self._session.get('/tv-series/{show}/seasons/{season}/clips'.format(show=show, season=season), params=params).json()

    def categories(self):
        self._refresh_token()
        return self._session.get('/genres', params={'device': 'web'}).json()['genres']

    def category(self, category):
        self._refresh_token()
        return self._session.get('/genres/{category}'.format(category=category), params={'device': 'web'}).json()

    @mem_cache.cached(60*2)
    def channels(self, region):
        self._refresh_token()
        params = {
            'device': 'web',
            'streamParams': 'web,chrome,windows',
            'region': region,
            'offset': 0,
        }
        return self._session.get(LIVESTREAM_URL, params=params).json()['data']['getLivestream']

    def get_brightcove_src(self, reference):
        if not reference.isdigit():
            reference = 'ref:{}'.format(reference)

        brightcove_url = BRIGHTCOVE_URL.format(BRIGHTCOVE_ACCOUNT, reference)
        resp = self._session.get(brightcove_url, headers={'BCOV-POLICY': BRIGHTCOVE_KEY})
        return util.process_brightcove(resp.json())

    def logout(self):
        userdata.delete('shared_token') #legacy
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('token_expires')
        mem_cache.empty()
        self.new_session()
