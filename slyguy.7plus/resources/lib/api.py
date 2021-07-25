from time import time

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data, process_brightcove
from slyguy.log import log

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(headers=HEADERS)
        self._set_authentication()

    def _set_authentication(self):
        access_token = userdata.get('access_token')
        if not access_token:
            self._session.headers.update({'authorization': 'Bearer {}'.format(DEFAULT_TOKEN)})
            return

        self._session.headers.update({'authorization': 'Bearer {}'.format(userdata.get('access_token'))})
        self.logged_in = True

    @mem_cache.cached(60*5)
    def _market_id(self):
        try:
            return self._session.get(MARKET_ID_URL, params={'apikey': 'web'}).json()['_id']
        except:
            log.debug('Failed to get market id')
            return '18'

    def search(self, query):
        params = {
            'searchTerm': query,
            'market-id': self._market_id(),
            'platform-id': 'Web',
            'size': 30,
        }

        return self._session.get('https://searchapi.swm.digital/3.0/api/Search', params=params).json()

    def content(self, slug):
        params = {
            'platform-id': 'web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': '4.3',
            'signedUp': 'True',
        }

        return self._session.get('https://component-cdn.swm.digital/content/{slug}'.format(slug=slug), params=params).json()

    def component(self, slug, component_id):
        params = {
            'platform-id': 'Web',
            'market-id': self._market_id(),
            'platform-version': '1.0.67393',
            'api-version': '4.3.0.0',
            'signedUp': 'True',
            'component-id': component_id,
        }

        return self._session.get('https://component.swm.digital/component/{slug}'.format(slug=slug), params=params).json()

    def video_player(self, slug):
        params = {
            'platform-id': 'Web',
            'market-id': self._market_id(),
            'api-version': '4.3.0.0',
            'signedUp': 'True',
            'platform-version': '1.0.67393',
        }

        return self._session.get('https://component.swm.digital/player/live/{slug}'.format(slug=slug), params=params).json()['videoPlayer']

    def play(self, account, reference, live):
        params = {
            'appId': '7plus',
            'deviceType': 'web',
            'platformType': 'web',
            'ppId': '',
            'deviceId': '63d5f1ba-4e6c-4f50-9b5f-d624cf907f55',
            'pc': 1000,
            'advertid': 'null',
            'accountId': account,
            'referenceId': reference,
            'deliveryId': 'csai',
            'tvid': 'null',
            'ozid': '7bd7ba65-f070-4164-9266-8ce94d25acb3',
        }

        if live:
            params['videoType'] = 'live'

        data = self._session.get('https://videoservice.swm.digital/playback', params=params).json()
        if 'media' not in data:
            raise APIError(data[0]['error_code'])

        return process_brightcove(data['media'])

    # def _oauth_token(self, payload):
    #     data = self._session.post('https://auth2.swm.digital/connect/token', data=payload, headers={'x-swm-apikey': SWM_API_KEY}).json()
    #     if 'Errors' in data:
    #         self.logout()
    #         raise APIError(data['Errors'][0]['Detail'])

    #     userdata.set('access_token', data['access_token'])
    #     userdata.set('expires', int(time()+data['expires_in']-30))

    #     if 'refresh_token' in data:
    #         userdata.set('refresh_token', data['refresh_token'])

    #     self._set_authentication()

    # def _refresh_token(self, force=False):
    #     if not force and userdata.get('expires', 0) > time() or not self.logged_in:
    #         return

    #     log.debug('Refreshing token')

    #     payload = {
    #         'platformId': 'android',
    #         'regsource': '7plus',
    #         'refreshToken': userdata.get('refresh_token'),
    #     }

    #     self._oauth_token(payload)

    # def login(self, username, password):
    #     self.logout()

    #     payload = {
    #         'loginID': username,
    #         'password': password,
    #         'apiKey': GIGYA_API_KEY,
    #         'format': 'json',
    #     }

    #     data = self._session.post('https://accounts.au1.gigya.com/accounts.login', data=payload).json()
    #     if 'errorMessage' in data:
    #         raise APIError(data['errorMessage'])

    #     cookie = {data['sessionInfo']['cookieName']: data['sessionInfo']['cookieValue']}

    #     payload = {
    #         'login_token': data['sessionInfo']['cookieValue'],
    #         'authMode': 'cookie',
    #         'apiKey': GIGYA_API_KEY,
    #         'format': 'json',
    #     }

    #     data = self._session.post('https://accounts.au1.gigya.com/accounts.getJWT', params=payload, cookies=cookie).json()
    #     if 'errorMessage' in data:
    #         raise APIError(data['errorMessage'])

    #     payload = {
    #         'platformId': 'android',
    #         'regsource': '7plus',
    #         'IdToken': data['id_token'],
    #     }

    #     self._oauth_token(payload)

    # def logout(self):
    #     mem_cache.empty()
    #     userdata.delete('access_token')
    #     userdata.delete('refresh_token')
    #     userdata.delete('expires')
    #     self.new_session()
