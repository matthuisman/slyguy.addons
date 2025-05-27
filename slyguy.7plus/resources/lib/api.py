import time

from slyguy import mem_cache, userdata
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import process_brightcove
from slyguy.log import log

from .constants import *
from .language import _
from .settings import settings, Region


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self._session = Session(headers=HEADERS)
        self.logged_in = True if userdata.get('access_token') else False

    def _market_id(self):
        @mem_cache.cached(60*5)
        def auto():
            try:
                return self._session.get('https://market-cdn.swm.digital/v1/market/ip/', params={'apikey': 'web'}).json()['_id']
            except:
                log.debug('Failed to get market id from IP. Default to Sydney')
                return Region.SYD

        if settings.REGION.value == Region.AUTO:
            market_id = auto()
        else:
            market_id = settings.REGION.value

        log.debug('Market ID: {}'.format(market_id))
        return market_id

    def nav(self):
        params = {
            'platform-id': 'web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': API_VERSION,
        }

        return self._session.get('https://component-cdn.swm.digital/content/nav', params=params).json()['items']

    def search(self, query):
        params = {
            'searchTerm': query,
            'market-id': self._market_id(),
            'api-version': '4.4',
            'platform-id': PLATFORM_ID,
            'platform-version': PLATFORM_VERSION,
        }

        return self._session.get('https://searchapi.swm.digital/3.0/api/Search', params=params).json()

    def content(self, slug):
        params = {
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
        }

        return self._session.get('https://component-cdn.swm.digital/content/{slug}'.format(slug=slug), params=params).json()

    def component(self, slug, component_id):
        params = {
            'component-id': component_id,
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
            'signedUp': 'True',
        }

        return self._session.get('https://component.swm.digital/component/{slug}'.format(slug=slug), params=params).json()

    def video_player(self, slug):
        params = {
            'platform-id': PLATFORM_ID,
            'market-id': self._market_id(),
            'platform-version': PLATFORM_VERSION,
            'api-version': API_VERSION,
            'signedUp': 'True',
        }

        return self._session.get('https://component.swm.digital/player/live/{slug}'.format(slug=slug), params=params).json()['videoPlayer']

    def device_code(self, location=False):
        self.logout()
        payload = {
            'platformId': PLATFORM_ID,
            'regSource': '7plus',
            'deviceId': settings.DEVICE_ID.value,
            'locationVerificationRequired': 'true' if location else 'false',
        }
        return self._session.post('https://auth2.swm.digital/account/device/authorize', data=payload).json()

    def device_login(self, device_code):
        payload = {
            'platformId': PLATFORM_ID,
            'regSource': '7plus',
            'deviceCode': device_code,
        }
        data = self._session.post('https://auth2.swm.digital/connect/token', data=payload).json()
        if 'access_token' not in data:
            return False

        userdata.set('access_token', data['access_token'])
        userdata.set('token_expires', int(time.time()) + data['expires_in'] - 30)
        userdata.set('refresh_token', data['refresh_token'])
        return True

    def _refresh_token(self, force=False):
        if not self.logged_in or (not force and userdata.get('token_expires', 0) > time.time()):
            return

        log.debug('Refreshing token')
        payload = {
            'platformId': PLATFORM_ID,
            'regSource': '7plus',
            'refreshToken': userdata.get('refresh_token'),
        }
        data = self._session.post('https://auth2.swm.digital/connect/token', data=payload).json()
        if 'access_token' not in data:
            raise Error(_.TOKEN_REFRESH_ERROR)

        userdata.set('access_token', data['access_token'])
        userdata.set('token_expires', int(time.time()) + data['expires_in'] - 30)
        userdata.set('refresh_token', data['refresh_token'])

    def play(self, account, reference, live):
        self._refresh_token()

        params = {
            'appId': '7plus',
            'deviceType': PLATFORM_ID,
            'platformType': 'tv',
            'deviceId': settings.DEVICE_ID.value,
            'pc': 3181, #postcode
            'advertid': 'null',
            'accountId': account,
            'referenceId': reference,
            'deliveryId': 'csai',
            'marketId': self._market_id(),
            'ozid': 'dc6095c7-e895-41d3-6609-79f673fc7f63',
            'sdkverification': 'true',
            'cp.encryptionType': 'cenc', #cbcs
            'cp.drmSystems': 'widevine',
            'cp.containerFormat': 'cmaf',
            'cp.supportedCodecs': 'avc',
            'cp.drmAuth': 'true',
        }

        if live:
            params['videoType'] = 'live'

        headers = {
            'Authorization': 'Bearer {}'.format(userdata.get('access_token') or DEFAULT_TOKEN),
        }
        data = self._session.get('https://videoservice.swm.digital/playback', params=params, headers=headers).json()
        if 'media' not in data:
            if 'error' in data:
                msg = data.get('description', data['error'])
                if data['error'] in ('location_verification_required',):
                    raise APIError(_(_.LOCATION_NEEDED, error=msg))
                elif data['error'] in ('video_not_in_market',):
                    raise APIError(_(_.LOCATION_WRONG, error=msg))
                else:
                    raise APIError(msg)
            else:
                raise APIError(data[0]['error_code'])

        item = process_brightcove(data['media'])
        return item

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('refresh_token')
        userdata.delete('token_expires')
        self.new_session()
