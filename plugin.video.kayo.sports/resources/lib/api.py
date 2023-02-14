from time import time

from slyguy import settings, userdata, mem_cache
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data
from slyguy.drm import is_wv_secure

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._auth_header = {}
        self._subscribed = None

        self._session = Session(HEADERS, base_url=API_URL)
        self._set_authentication()

    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            return

        self._auth_header = {'authorization': 'Bearer {}'.format(access_token)}
        self.logged_in = True

    def is_subscribed(self):
        if self._subscribed is not None:
            return self._subscribed

        if not self.logged_in:
            return False

        data = jwt_data(userdata.get('access_token'))
        self._subscribed = data['https://kayosports.com.au/status']['account_status'] == 'ACTIVE_SUBSCRIPTION'
        return self._subscribed

    def _oauth_token(self, data, _raise=True):
        token_data = self._session.post(AUTH_URL + '/token', json=data, headers={'User-Agent': 'okhttp/3.10.0'}, error_msg=_.TOKEN_ERROR).json()

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
            'client_id': CLIENT_ID,
            'audience' : 'streamotion.com.au',
            'scope': 'openid offline_access drm:{} email'.format('high' if is_wv_secure() else 'low'),
        }

        return self._session.post(AUTH_URL + '/device/code', data=payload).json()

    def device_login(self, device_code):
        payload = {
            'client_id': CLIENT_ID,
            'device_code' : device_code,
            'scope': 'openid offline_access drm:{}'.format('high' if is_wv_secure() else 'low'),
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
            'client_id': CLIENT_ID,
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'openid offline_access drm:{} email'.format('high' if is_wv_secure() else 'low'),
        }

        self._oauth_token(payload)

    def login(self, username, password):
        payload = {
            'client_id': CLIENT_ID,
            'username': username,
            'password': password,
            'audience': 'streamotion.com.au',
            'scope': 'openid offline_access drm:{} email'.format('high' if is_wv_secure() else 'low'),
            'grant_type': 'http://auth0.com/oauth/grant-type/password-realm',
            'realm': 'prod-martian-database',
        }

        self._oauth_token(payload)
        self._refresh_token(force=True)

    def profiles(self):
        self._refresh_token()
        return self._session.get(PROFILE_URL + '/user/profile', headers=self._auth_header).json()

    def add_profile(self, name, avatar_id):
        self._refresh_token()

        payload = {
            'name': name,
            'avatar_id': avatar_id,
            'onboarding_status': 'welcomeScreen',
        }

        return self._session.post(PROFILE_URL + '/user/profile', json=payload, headers=self._auth_header).json()

    def delete_profile(self, profile):
        self._refresh_token()
        return self._session.delete(PROFILE_URL + '/user/profile/' + profile['id'], headers=self._auth_header)

    def profile_avatars(self):
        return self._session.get(RESOURCE_URL + '/production/avatars/avatars.json').json()

    def use_cdn(self, live=False):
        self._refresh_token()
        live = True #Force live like the website does
        url = CDN_URL + '/web/usecdn/android/' + 'LIVE' if live else 'VOD'
        return self._session.get(url, headers=self._auth_header).json()

    def channel_data(self):
        try:
            return self._session.get(LIVE_DATA_URL).json()
        except:
            return {}

    def landing(self, name, sport=None, series=None, team=None):
        self._refresh_token()

        params = {
            'evaluate': 5,
        }

        if sport:
            params['sport'] = sport

        if series:
            params['series'] = series

        if team:
            params['team'] = team

        return self._session.get('/content/types/landing/names/' + name, params=params, headers=self._auth_header).json()

    def panel(self, href):
        self._refresh_token()

        params = {}
        if '/private/' in href:
            params['profile'] = userdata.get('profile_id')

        return self._session.get(href, params=params, headers=self._auth_header).json()

    def show(self, show_id, season_id=None):
        self._refresh_token()

        params = {
            'evaluate': 3,
            'show': show_id,
        }
        if season_id:
            params['season'] = season_id

        return self._session.get('/content/types/landing/names/show', params=params, headers=self._auth_header).json()

    def search(self, query, page=1, size=250):
        self._refresh_token()

        params = {
            'q': query,
            'size': size,
            'page': page,
        }

        return self._session.get('/search/types/landing', params=params).json()

    def stream(self, asset_id):
        self._refresh_token()

        payload = {
            'assetId': asset_id,
            'canPlayHevc': settings.common_settings.getBool('h265', False),
           # 'contentType': 'application/xml+dash',
           # 'drm': True,
            'forceSdQuality': False,
            'playerName': 'exoPlayerTV',
            'udid': UDID,
        }

        data = self._session.post(PLAY_URL + '/play', json=payload, headers=self._auth_header).json()
        if ('status' in data and data['status'] != 200) or 'errors' in data:
            msg = data.get('detail') or data.get('errors', [{}])[0].get('detail')
            raise APIError(_(_.ASSET_ERROR, msg=msg))

        return data['data'][0]

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        self.new_session()
