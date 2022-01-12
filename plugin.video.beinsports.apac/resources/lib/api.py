import json

import arrow

from slyguy import userdata, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _

class APIError(Error):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False

        self._session = Session(HEADERS, base_url=API_BASE)
        self._set_authentication()

    def _set_authentication(self):
        token = userdata.get('token')
        if not token:
            return

        self._session.cookies.update({TOKEN_COOKIE_KEY: token})
        self.logged_in = True

    def require_token(self):
        if TOKEN_COOKIE_KEY in self._session.cookies:
            return

        app_version = self._session.get(APP_VERSION_URL).text.strip()

        payload = {
            "BuildNo": "9999",
            "ClientVersion": app_version,
            "DeviceBrand": "Nvidia",
            "DeviceFirmwareVersion": "27",
            "DeviceId": "4jhrpoUfUr1Dxmbf",
            "DeviceManufacturer": "Nvidia",
            "DeviceModel": "Shield",
            "DeviceName": "AndroidTv",
            "IsRoot": "false",
            "MacAddress": "00:00:00:00:00:00",
        }

        data = self._session.post('/api/configuration/appconfig', json=payload).json()
        if not data['Data']:
            raise APIError(data['Message']['Title'])

        self._session.cookies.update({TOKEN_COOKIE_KEY: data['Data']['AccessToken']})

    def device_code(self):
        self.logout()
        self.require_token()
        return self._session.post('/api/account/generateauthcode').json()['Data']

    def device_login(self, code):
        self.require_token()

        payload = {
            'AuthCode': code,
        }

        data = self._session.post('/api/account/loginwithauthcode', json=payload).json()['Data']
        if not data:
            return

        token = data['User']['AccessToken']
        userdata.set('token', token)
        self._set_authentication()

        return True

    def login(self, username, password):
        self.logout()
        self.require_token()

        payload = {
            'Action' : '/View/Account/SubmitLogin',
            'jsonModel': json.dumps({
                'Username': username,
                'Password': password,
                'IsOnboarding': False,
                'IsVoucher': False,
            }),
            'captcha': '',
        }

        resp  = self._session.post('/View/Account/SubmitLogin', json=payload)
        token = resp.cookies.get(TOKEN_COOKIE_KEY)

        if not token:
            raise APIError(_.LOGIN_ERROR)

        userdata.set('token', token)
        self._set_authentication()

    def live_channels(self):
        items = []

        for i in range(10):
            payload = {
                'Page': i,
                'PageSize': PAGESIZE,
            }

            data = self._session.post('/api/broadcast/channels', json=payload).json()['Data']
            items.extend(data['Items'])

            if len(data['Items']) < PAGESIZE:
                break

        return items

    def epg(self, days=3):
        start = arrow.utcnow()
        end   = start.shift(days=days)

        payload = {
            'StartTime': start.format('YYYY-MM-DDTHH:mm:00.000') + 'Z',
            'EndTime':   end.format('YYYY-MM-DDTHH:mm:00.000') + 'Z',
            'OnlyLiveEvents': False,
          #  'ChannelId': 'beinsports1',
        }

        return self._session.post('/api/broadcast/tvguide', json=payload).json()['Data']['Items']

    def catch_up(self, _type=0, catalog_id='CATCHUP'):
        items = []

        for i in range(10):
            payload = {
                'Page': i,
                'PageSize': PAGESIZE,
                'Type': _type,
                'CatalogId': catalog_id,
            }

            data = self._session.post('/api/content/catchups', json=payload).json()['Data']

            rows = data.get('Items', [])
            if not rows:
                break

            items.extend(rows)
            if len(rows) < PAGESIZE:
                break

        return items

    def play(self, channel_id=None, vod_id=None):
        payload = {
            'ChannelId': channel_id,
            'VodId': vod_id,
        }

        data = self._session.post('/api/play/play', json=payload).json()
        if not data['Data']:
            try: error = data['Message']['Text']
            except: error = _.NO_STREAM
            raise APIError(error)

        return data['Data']

    def logout(self):
        userdata.delete('token')
        self.new_session()