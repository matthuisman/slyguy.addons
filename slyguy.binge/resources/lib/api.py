from time import time

from slyguy import settings, userdata
from slyguy.log import log
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.drm import is_wv_secure

from streamotion.api import API as BaseAPI

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(BaseAPI):
    BASE_URL = API_URL
    CLIENT_ID = CLIENT_ID

    def channel_data(self):
        try:
            return self._session.get(LIVE_DATA_URL)
        except:
            return {}

    def search(self, query):
        params = {
            'q': query,
        }

        return self._session.get('/search/types/landing', params=params)

    #landing has heros and panels
    def landing(self, name, params=None):
        _params = {
            'evaluate': 4,
        }

        _params.update(params or {})

        return self._session.get('/content/types/landing/names/{}'.format(name), params=params)

    def panel(self, link=None, panel_id=None):
        self._refresh_token()
        params = {'profile': userdata.get('profile_id')}

        if panel_id:
            url = '/private/panels/{panel_id}' if self.logged_in else '/panels/{panel_id}'
            link = url.format(panel_id=panel_id)

        return self._session.get(link, params=params, headers=self._auth_header)

    def use_cdn(self, live=False):
        return self._session.get('https://cdnselectionserviceapi.binge.com.au/web/usecdn/unknown/{media}'.format(media='LIVE' if live else 'VOD'), headers=self._auth_header)

    def profiles(self):
        self._refresh_token()
        return self._session.get('https://profileapi.streamotion.com.au/user/profile/type/ares', headers=self._auth_header)

    def license_headers(self):
        self._refresh_token()
        return self._auth_header

    def asset(self, asset_id):
        self._refresh_token()
        params = {'profile': userdata.get('profile_id')}
        return self._session.get('/private/assets/{}'.format(asset_id), params=params, headers=self._auth_header)

    def up_next(self, asset_id):
        data = self.landing('next', params={'asset': asset_id})
        for panel in data.get('panels', []):
            if panel.get('countdown') and panel.get('contents'):
                return panel['contents'][0]
        return None

    def token_service(self):
        payload = {
            'client_id': CLIENT_ID,
            'scope': 'openid email drm:{}'.format('high' if is_wv_secure() else 'low'),
        }
        data = self._session.post('https://tokenservice.streamotion.com.au/oauth/token', json=payload, headers=self._auth_header)
        return data['access_token']

    def profile(self, profile_id):
        data = self._session.get('https://profileapi.streamotion.com.au/user/profile/type/ares/{}'.format(profile_id), headers=self._auth_header)
        if 'status' in data and data['status'] != 200:
            raise APIError(_.PROFILE_MISSING)
        return data

    def tracking_ids(self, url):
        ids = []
        try:
            data = self._session.get(url)
            for row in data.get('avails') or []:
                for ad in row.get('ads') or []:
                    ids.append(ad['adId'])
        except Exception as e:
            log.exception(e)
            log.debug('Failed to obtain tracking ids')

        return ids

    def stream(self, asset_id):
        self._refresh_token()

        payload = {
            'assetId': asset_id,
            'application': {'name':'binge', 'appId':'binge.com.au'},
            'device':{'id':UDID, 'type':'android'},
            'player':{'name':'exoPlayerTV'},
            'ads':{'optOut': False},
            'capabilities':{'codecs':['avc']},
            'session':{'intent':'playback'}
        }

        if settings.getBool('hevc', False):
            payload['capabilities']['codecs'].append('hevc')

        token = self.token_service()
        headers = {'authorization': 'Bearer {}'.format(token)}
        headers['x-vimond-subprofile'] = self.profile(userdata.get('profile_id')).get('vimond_token')

        data = self._session.post('https://play.binge.com.au/api/v3/play', json=payload, headers=headers)
        if ('status' in data and data['status'] != 200) or 'errors' in data:
            msg = data.get('detail') or data.get('errors', [{}])[0].get('detail')
            raise APIError(_(_.ASSET_ERROR, msg=msg))

        return data
