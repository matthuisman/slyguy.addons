from slyguy import settings, userdata
from slyguy.log import log
from slyguy.exceptions import Error

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
            return self._session.gz_json(LIVE_DATA_URL)
        except:
            log.debug('Failed to get: {}'.format(LIVE_DATA_URL))
            return {}

    #landing has heros and panels
    def landing(self, name, params=None):
        _params = {
            'evaluate': 4,
        }

        _params.update(params or {})

        return self._session.get('/content/types/landing/names/{}'.format(name), params=params)
    
    def _check_errors(self, data):
        if 'violations' in data:
            raise APIError('{field} {message}'.format(**data['violations'][0]))

        if ('status' in data and data['status'] != 200) or 'errors' in data:
            msg = data.get('detail') or data.get('errors', [{}])[0].get('detail')
            raise APIError(msg)

    def panel(self, link=None, panel_id=None, channel_id=None):
        self._refresh_token()

        params = {
            'profile': userdata.get('profile_id') or '%20'
        }

        if channel_id:
            params['channel'] = channel_id

        if panel_id:
            url = '/private/panels/{panel_id}' if self.logged_in else '/panels/{panel_id}'
            link = url.format(panel_id=panel_id)

        data = self._session.get(link, params=params, headers=self._auth_header)
        self._check_errors(data)
        return data

    def use_cdn(self, live=False):
        return self._session.get('https://cdnselectionserviceapi.flashnews.com.au/mobile/usecdn/unknown/{media}'.format(media='LIVE' if live else 'VOD'), headers=self._auth_header)

    def profiles(self):
        self._refresh_token()
        try:
            return self._session.get('https://profileapi.streamotion.com.au/user/profile/type/flash', headers=self._auth_header)
        except:
            return []

    def stream(self, asset_id):
        self._refresh_token()

        payload = {
            'assetId': asset_id,
            'canPlayHevc': settings.getBool('hevc', False),
            'contentType': 'application/xml+dash',
            'drm': True,
            'forceSdQuality': False,
            'playerName': 'exoPlayerTV',
            'udid': UDID,
        }

        data = self._session.post('https://play.flashnews.com.au/api/v1/play', json=payload, headers=self._auth_header)
        self._check_errors(data)
        return data['data'][0]
