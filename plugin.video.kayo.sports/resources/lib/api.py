import uuid
from slyguy import settings, userdata
from slyguy.exceptions import Error
from slyguy.util import jwt_data

from streamotion.api import API as BaseAPI

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(BaseAPI):
    BASE_URL = API_URL
    CLIENT_ID = CLIENT_ID

    def is_subscribed(self):
        if self._subscribed is not None:
            return self._subscribed

        if not self.logged_in:
            return False

        data = jwt_data(userdata.get('access_token'))
        self._subscribed = data['https://kayosports.com.au/status']['account_status'] == 'ACTIVE_SUBSCRIPTION'
        return self._subscribed

    def profiles(self):
        self._refresh_token()
        return self._session.get(PROFILE_URL + '/user/profile', headers=self._auth_header)

    def add_profile(self, name, avatar_id):
        self._refresh_token()

        payload = {
            'name': name,
            'avatar_id': avatar_id,
            'onboarding_status': 'welcomeScreen',
        }

        return self._session.post(PROFILE_URL + '/user/profile', json=payload, headers=self._auth_header)

    def delete_profile(self, profile):
        self._refresh_token()
        return self._session.delete(PROFILE_URL + '/user/profile/' + profile['id'], headers=self._auth_header)

    def profile_avatars(self):
        return self._session.get(RESOURCE_URL + '/production/avatars/avatars.json')

    def use_cdn(self, live=False):
        self._refresh_token()
        live = True #Force live like the website does
        url = CDN_URL + '/web/usecdn/android/' + 'LIVE' if live else 'VOD'
        return self._session.get(url, headers=self._auth_header)

    def channel_data(self):
        try:
            return self._session.get(LIVE_DATA_URL)
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

        return self._session.get('/content/types/landing/names/' + name, params=params, headers=self._auth_header)

    def panel(self, href):
        self._refresh_token()

        params = {}
        if '/private/' in href:
            params['profile'] = userdata.get('profile_id')

        return self._session.get(href, params=params, headers=self._auth_header)

    def show(self, show_id, season_id=None):
        self._refresh_token()

        params = {
            'evaluate': 3,
            'show': show_id,
        }
        if season_id:
            params['season'] = season_id

        return self._session.get('/content/types/landing/names/show', params=params, headers=self._auth_header)

    def search(self, query, page=1, size=250):
        self._refresh_token()

        params = {
            'q': query,
            'size': size,
            'page': page,
        }

        return self._session.get('/search/types/landing', params=params)

    def stream(self, asset_id):
        self._refresh_token()

        payload = {
            'assetId': asset_id,
            'canPlayHevc': settings.common_settings.getBool('h265', False),
           # 'contentType': 'application/xml+dash',
           # 'drm': True,
            'forceSdQuality': False,
            'playerName': 'exoPlayerTV',
            'udid': str(uuid.uuid4()),
        }

        data = self._session.post(PLAY_URL + '/play', json=payload, headers=self._auth_header)
        if ('status' in data and data['status'] != 200) or 'errors' in data:
            msg = data.get('detail') or data.get('errors', [{}])[0].get('detail')
            raise APIError(_(_.ASSET_ERROR, msg=msg))

        return data['data'][0]
