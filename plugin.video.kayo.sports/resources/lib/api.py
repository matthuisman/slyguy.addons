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

        self._session = Session(HEADERS)
        self._set_authentication()

    @mem_cache.cached(60*10)
    def _config(self):
        return self._session.get(CONFIG_URL).json()

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
        token_data = self._session.post('https://auth.streamotion.com.au/oauth/token', json=data, headers={'User-Agent': 'okhttp/3.10.0'}, error_msg=_.TOKEN_ERROR).json()

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

    def device_code(self):
        payload = {
            'client_id': CLIENT_ID,
            'audience' : 'streamotion.com.au',
            'scope': 'openid offline_access drm:{} email'.format('high' if is_wv_secure() else 'low'),
        }

        return self._session.post('https://auth.streamotion.com.au/oauth/device/code', data=payload).json()

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
        return self._session.get('{host}/user/profile'.format(host=self._config()['endPoints']['profileAPI']), headers=self._auth_header).json()

    def add_profile(self, name, avatar_id):
        self._refresh_token()

        payload = {
            'name': name,
            'avatar_id': avatar_id,
            'onboarding_status': 'welcomeScreen',
        }

        return self._session.post('{host}/user/profile'.format(host=self._config()['endPoints']['profileAPI']), json=payload, headers=self._auth_header).json()

    def delete_profile(self, profile):
        self._refresh_token()

        return self._session.delete('{host}/user/profile/{profile_id}'.format(host=self._config()['endPoints']['profileAPI'], profile_id=profile['id']), headers=self._auth_header)

    def profile_avatars(self):
        return self._session.get('{host}/production/avatars/avatars.json'.format(host=self._config()['endPoints']['resourcesAPI'])).json()

    def sport_menu(self):
        return self._session.get('{host}/production/sport-menu/lists/default.json'.format(host=self._config()['endPoints']['resourcesAPI'])).json()

    def use_cdn(self, live=False, sport=None):
        return self._session.get('{host}/usecdn/mobile/{media}'.format(host=self._config()['endPoints']['cdnSelectionServiceAPI'], media='LIVE' if live else 'VOD'), params={'sport': sport}, headers=self._auth_header).json()

    #landing has heros and panels
    def landing(self, name, sport=None):
        params = {
            'evaluate': 3,
            'profile': userdata.get('profile_id'),
        }

        if sport:
            params['sport'] = sport

        return self._session.get('{host}/content/types/landing/names/{name}'.format(host=self._config()['endPoints']['contentAPI'], name=name), params=params, headers=self._auth_header).json()

    def channel_data(self):
        try:
            return self._session.get(LIVE_DATA_URL).json()
        except:
            return {}

    #panel has shows and episodes
    def panel(self, id, sport=None):
        params = {
            'evaluate': 3,
            'profile': userdata.get('profile_id'),
        }

        if sport:
            params['sport'] = sport

        return self._session.get('{host}/content/types/carousel/keys/{id}'.format(host=self._config()['endPoints']['contentAPI'], id=id), params=params, headers=self._auth_header).json()[0]

    #show has episodes and panels
    def show(self, show_id, season_id=None):
        params = {
            'evaluate': 3,
            'showCategory': show_id,
            'seasonCategory': season_id,
            'profile': userdata.get('profile_id'),
        }

        return self._session.get('{host}/content/types/landing/names/show'.format(host=self._config()['endPoints']['contentAPI']), params=params, headers=self._auth_header).json()

    def search(self, query, page=1, size=250):
        params = {
            'q': query,
            'size': size,
            'page': page,
        }

        return self._session.get('{host}/v2/search'.format(host=self._config()['endPoints']['contentAPI']), params=params).json()

    def event(self, id):
        params = {
            'evaluate': 3,
            'event': id,
        }

        return self._session.get('{host}/content/types/landing/names/event'.format(host=self._config()['endPoints']['contentAPI']), params=params).json()[0]['contents'][0]['data']['asset']

    def stream(self, asset_id):
        self._refresh_token()

        params = {
            'fields': 'alternativeStreams,assetType,markers,metadata.isStreaming,metadata.drmContentIdAvc,metadata.sport',
        }

        data = self._session.post('{host}/api/v1/asset/{asset_id}/play'.format(host=self._config()['endPoints']['vimondPlayAPI'], asset_id=asset_id), params=params, json={}, headers=self._auth_header).json()
        if ('status' in data and data['status'] != 200) or 'errors' in data:
            msg = data.get('detail') or data.get('errors', [{}])[0].get('detail')
            raise APIError(_(_.ASSET_ERROR, msg=msg))

        return data['data'][0]

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('expires')
        self.new_session()
