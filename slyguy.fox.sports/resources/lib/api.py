import uuid
from time import time

from slyguy import userdata, mem_cache, settings
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.util import jwt_data
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
            return

        self._session.headers.update({'authorization': access_token})
        self.logged_in = True

    def _config(self):
        config = mem_cache.get('_config')
        if not config:
            config = self._session.get(CONFIG_URL).json()
            mem_cache.set('_config', config, 60*10)

        self._session.headers.update({'x-api-key': config['api']['key']})
        return config

    def _check_token(self):
        if self.logged_in and userdata.get('expires', 0) < time():
            if not self.check_auth(userdata.get('device_id')):
                self.logout()
                raise APIError(_.ERROR_REFRESH_TOKEN)

    @mem_cache.cached(60*5)
    def live(self):
        config = self._config()
        return self._session.get(config['api']['content']['live']).json()['panels']['member']

    @mem_cache.cached(60*10)
    def entitlements(self):
        config = self._config()

        params = {
            'device_type': '',
            'device_id': userdata.get('device_id'),
            'resource': '',
            'requestor': '',
        }

        return self._session.get(config['api']['auth']['getentitlements'], params=params).json()['entitlements']

    def provider_login(self):
        self.logout()

        config = self._config()
        device_id = str(uuid.uuid1().hex)[:16]

        payload = {
            'email': '',
            'password': '',
            'deviceId': device_id,
            'facebookToken': '',
            'googleToken': ''
        }

        data = self._session.post(config['api']['profile']['login'], json=payload).json()
        self._session.headers.update({'authorization': 'Bearer {}'.format(data['accessToken'])})

        payload = {
            'deviceID': device_id,
            'isMvpd': True,
            'selectedMvpdId': ''
        }

        data = self._session.post(config['api']['auth']['accountRegCode'], json=payload).json()

        result = {
            'device_id': device_id,
            'code': data['code'],
            'url': 'https://'+config['auth']['displayActivationUrl'],
            'timeout': int(data['expires'] - time() - 12)
        }

        return result

    def check_auth(self, device_id):
        config = self._config()
        data = self._session.get(config['api']['auth']['checkadobeauthn'], params={'device_id': device_id}).json()
        if not data.get('accessToken'):
            return False

        userdata.set('device_id', device_id)
        userdata.set('access_token', data['accessToken'])
        userdata.set('expires', min(int(data['tokenExpiration']/1000)-30, int(time() + 86400)))
        return True

    def play(self, stream_id, stream_type='live'):
        self._check_token()
        config = self._config()

        if settings.getBool('enable_4k', True):
            max_res = 'UHD/HDR' if settings.getBool('enable_hdr', False) else 'UHD/SDR'
        else:
            max_res = '720p'

        payload = {
            'deviceHeight': 2160,
            'deviceWidth': 3840,
            'os': 'Android',
            'osv': '9.0.0',
            'streamType': stream_type, #live, liveRestart, vod
            'streamId': stream_id, #EPGListing ID
            'maxRes': max_res, #720p, UHD/HDR, UHD/SDR
        }

        data = self._session.post(config['api']['content']['watch'], json=payload).json()
        if 'url' not in data:
            error = data.get('message') or _.NO_VIDEO_FOUND
            raise APIError(error)

        data = self._session.get(data['url'], headers={'authorization': None}).json()
        if 'isException' in data:
            raise APIError(data['description'])

        return data['playURL']

    def _logout_provider(self):
        config = self._config()
        self._session.delete(config['api']['auth']['logoutmvpd']).json()

    def logout(self):
        if userdata.get('access_token'):
            try: self._logout_provider()
            except: pass

        userdata.delete('access_token')
        userdata.delete('device_id')
        userdata.delete('expires')
        mem_cache.empty()
        self.new_session()
