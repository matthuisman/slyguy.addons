import time
import hmac
import hashlib
import base64
import json

import arrow
from six.moves.urllib.parse import urlencode
from slyguy import userdata, mem_cache, gui
from slyguy.util import jwt_data, hash_6
from slyguy.session import Session
from slyguy.exceptions import Error

from .constants import *
from .language import _
from .settings import settings, Login


class APIError(Error):
    pass


class API(object):
    def new_session(self):
        self.logged_in = False
        self._auth_headers = {}
        self._config = {}

        self._session = Session(headers=HEADERS)
        self._session.after_request = self._check_response

        self._set_authentication()

    @mem_cache.cached(60*60, key='config')
    def get_config(self):
        try:
            return self._session.get(APP_DATA_URL).json()['settings']
        except Exception as e:
            raise APIError('Failed to download app settings')

    @mem_cache.cached(60*60)
    def _app_version(self):
        return self._session.get(APP_VERSION_URL).text.strip()

    def _set_authentication(self):
        device_token = userdata.get('device_token')
        auth_token = userdata.get('auth_token')

        if not device_token or not auth_token:
            return

        self._auth_headers = {
            'X-AN-WebService-CustomerAuthToken': auth_token,
            'X-AN-WebService-DeviceAuthToken': device_token,
        }

        self.logged_in = True

    def _create_session(self, force=False):
        self._config = self.get_config()
        platform = self._config['alpha_networks_dash'][REGION]

        self._session._base_url = platform['platform_url']+'{}'
        self._session.headers.update({
            'X-AN-WebService-IdentityKey': platform['hss_key'], # hss_key, hls_key, chromecast_key
        })

        if not self.logged_in or (not force and time.time() < userdata.get('token_expires')):
            return

        login_type = settings.LOGIN_TYPE.value

        if login_type == Login.MULTI_IP:
            # Single device, changing IP address (same as app)
            data = self._session.post('proxy/loginDevice', headers=self._auth_headers).json()

        elif login_type == Login.MULTI_DEVICE:
            # Multiple device, static IP address
            data = self._session.post('proxy/casAvailableDevice', headers=self._auth_headers).json()

        elif login_type == Login.PASSWORD and userdata.get('login_data'):
            # Supports multiple devices and multiple IP address as long (as others also using password)
            data = userdata.get('login_data')
            data = self._session.post(data.pop('url'), data=data).json()
            auth_token = data['result']['newAuthToken']
            device_token = data['result']['deviceAuthToken']
            selected = userdata.get('device_data')
            data = {
                'name': selected['name'],
                'casDeviceId': selected['uniqueDeviceId'],
                'type': selected['type'],
            }
            data = self._session.post('proxy/casAuth', data=data, headers={'X-AN-WebService-CustomerAuthToken': auth_token, 'X-AN-WebService-DeviceAuthToken': device_token}).json()
        else:
            raise APIError('Unable to persist session. Try logout and login again.')

        if data['error']:
            error = _(_.TOKEN_ERROR, msg=data['error']['message'])

            if data['error']['code'] == -1:
                self.logout()
                gui.refresh()

                if login_type == Login.MULTI_IP:
                    error = _.LOGIN_MULTI_IP_ERROR
                elif login_type == Login.MULTI_DEVICE:
                    error = _.LOGIN_MULTI_DEVICE_ERROR

            raise APIError(error)

        if 'deviceAuthToken' in data['result']:
            userdata.set('device_token', data['result']['deviceAuthToken'])

        self._set_auth(data['result']['newAuthToken'])

    def _set_auth(self, auth_token):
        token_data = jwt_data(auth_token)
        userdata.set('auth_token', auth_token)
        userdata.set('token_expires', token_data['exp'] - 30)
        self._set_authentication()

    def _select_device(self, token):
        data = self._session.post('proxy/casAvailableDevice', headers={'X-AN-WebService-CustomerAuthToken': token}).json()
        devices = data['result'].get('device', [])

        while True:
            if devices:
                options = []
                values = []
                for row in devices:
                    options.append(_(_.DEVICE_LABEL, name=row['name'], last_login=arrow.get(row['lastLoginDate']).to('local').format('D MMMM YYYY')))
                    values.append(row)

                options.append(_.NEW_DEVICE)
                values.append('new')

                options.append(_.REMOVE_DEVICE)
                values.append('remove')

                index = gui.select(_.SELECT_DEVICE, options=options)
                if index == -1:
                    return

                selected = values[index]
            else:
                selected = 'new'

            if selected == 'new':
                device_name = gui.input(_.DEVICE_NAME).strip()

                if not device_name or not gui.yes_no(_(_.NEW_CONFIRM, device_name=device_name)):
                    if devices:
                        continue
                    else:
                        return

                return {
                    'uniqueDeviceId': hash_6('{}{}'.format(int(time.time()), device_name), length=16),
                    'name': device_name,
                    'type': 'Android',
                }

            elif selected == 'remove':
                options = []
                values = []

                for row in devices:
                    options.append(row['name'])
                    values.append(row)

                to_remove = None
                while not to_remove:
                    index = gui.select(_.SELECT_REMOVE_DEVICE, options=options)
                    if index == -1:
                        break

                    if gui.yes_no(_(_.REMOVE_CONFIRM, device_name=values[index]['name'])):
                        to_remove = values[index]

                if not to_remove:
                    continue

                data = {
                    'casDeviceId':  to_remove['uniqueDeviceId'],
                }

                data = self._session.post('proxy/casRemoveDevice', data=data, headers={'X-AN-WebService-CustomerAuthToken': token}).json()
                if data['error']:
                    gui.error(data['error']['message'])
                    continue

                return self._select_device(data['result']['newAuthToken'])
            else:
                return selected

    def _check_response(self, resp):
        if resp.ok:
            return

        if resp.status_code == 451:
            raise APIError(_.GEO_BLOCKED)
        else:
            raise APIError(_(_.HTTP_ERROR, code=resp.status_code))

    def login(self, username, password, _type=LOGIN_CONNECT):
        self.logout()
        self._create_session()

        if _type == LOGIN_SATELLITE:
            login_data = {
                'userId': 'unknown',
                'providerId': 'sbs',
                'tveAdapter': 'sbs',
                'tveParams': json.dumps({"username":username,"password":hashlib.md5(password.encode('utf8')).hexdigest()}),
            }
            login_url = 'proxy/loginFromTve'
        else:
            login_data = {
                'password': password,
                'email': username,
            }
            login_url = 'proxy/login'

        data = self._session.post(login_url, data=login_data).json()
        if data['error']:
            raise APIError(_(_.LOGIN_ERROR, msg=data['error']['message']))

        auth_token = data['result']['newAuthToken']

        while True:
            selected = self._select_device(auth_token)
            if not selected:
                return

            login_data['deviceId'] = selected['uniqueDeviceId']

            data = self._session.post(login_url, data=login_data).json()
            if data['error']:
                gui.error(data['error']['message'])
            else:
                break

        auth_token = data['result']['newAuthToken']
        device_token = data['result']['deviceAuthToken']
        userdata.set('device_token', device_token)

        data = {
            'name': selected['name'],
            'casDeviceId': selected['uniqueDeviceId'],
            'type': selected['type'],
        }

        data = self._session.post('proxy/casAuth', data=data, headers={'X-AN-WebService-CustomerAuthToken': auth_token, 'X-AN-WebService-DeviceAuthToken': device_token}).json()
        if data['error']:
            raise APIError(data['error']['message'])

        self._set_auth(data['result']['newAuthToken'])
        mem_cache.delete('channels')

        if settings.LOGIN_TYPE.value == Login.PASSWORD:
            login_data['url'] = login_url
            userdata.set('login_data', login_data)
            userdata.set('device_data', selected)

    @mem_cache.cached(60*10, key='channels')
    def channels(self):
        self._create_session()

        payload = {
            'languageId': 'eng',
        }

        channels = []
        for row in self._session.post('proxy/listChannels', data=payload).json()['result']['channels']:
            row['logo'] = '{}proxy/imgdata?objectId=75_{}&type=102'.format(self._config['alpha_networks_dash'][REGION]['platform_url'], row['idChannel'])
            channels.append(row)

        return sorted(channels, key=lambda x: x.get('sorting', x['localizeNumber']))

    def license_request(self, channel_id):
        self._create_session()

        app_version = self._app_version()
        params = {
            'wskey': self._session.headers['X-AN-WebService-IdentityKey'],
            'playerName': PLAYER_NAME,
            'checksum': self._checksum(channel_id, app_version),
            'playerVersion': app_version,
            'idChannel': channel_id,
        }

        headers = self._auth_headers
        headers['X-Idviu-Widevine-Key-Id'] = 'eue7pcj4RyyWZF+Srip5kQ=='

        url = self._session._base_url.format('arkena/askLicenseWV?' + urlencode(params))
        return url, headers

    def heartbeat(self, channel_id):
        self._create_session()

        payload = {
            'idChannel': channel_id,
            'streamAction': 'play',
            'authToken': userdata.get('auth_token'),
            'streamRate': 0,
            'isTimeshiftUsed': 'true',
            'type': 'AndroidPhone',
        }

        data = self._session.post('proxy/viewRights', data=payload, headers=self._auth_headers).json()
        if 'newAuthToken' in data['result']:
            self._set_auth(data['result']['newAuthToken'])

    def play(self, channel_id):
        self._create_session(force=True)

        app_version = self._app_version()
        payload = {
            'idChannel': channel_id,
            'playerName': PLAYER_NAME,
            'playerVersion': app_version,
            'checksum': self._checksum(channel_id, app_version),
            'languageId': 'eng',
            'authToken': userdata.get('auth_token'),
        }

        data = self._session.post('proxy/channelStream', data=payload, headers=self._auth_headers).json()
        if data.get('error'):
            raise APIError(data['error']['message'])

        if 'newAuthToken' in data['result']:
            self._set_auth(data['result']['newAuthToken'])

        return data['result']['url']

    def epg(self, ids, start, end):
        self._create_session()

        data = {
            '$and': [
                {'id_channel': {'$in': ids}},
                start,
                end,
            ]
        }

        params = {
            'languageId': 'eng',
            'filter': json.dumps(data, separators=(',', ':')),
        }

        data = self._session.get('cms/epg/filtered', params=params).json()
        if data['error']:
            raise APIError(data['error']['message'])

        epg = {}
        for key in data['result']['epg']:
            for row in data['result']['epg'][key]:
                channel_id = row.pop('id_channel')
                if channel_id not in epg:
                    epg[channel_id] = []
                epg[channel_id].append(row)

        return epg

    def _checksum(self, channel_id, app_version):
        checksum = userdata.get('auth_token', '') + str(channel_id) + app_version
        checksum = hmac.new(SECRET_KEY.encode('utf8'), msg=checksum.encode('utf8'), digestmod=hashlib.sha256).digest()
        return base64.b64encode(checksum).decode('utf8')

    def logout(self):
        userdata.delete('password')
        userdata.delete('device_id')
        userdata.delete('device_token')
        userdata.delete('auth_token')
        userdata.delete('token_expires')

        mem_cache.delete('config')
        mem_cache.delete('channels')

        self.new_session()