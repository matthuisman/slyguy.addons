import uuid
from time import time

import arrow
from kodi_six import xbmc

from slyguy import userdata, settings, mem_cache
from slyguy.session import Session
from slyguy.exceptions import Error
from slyguy.log import log
from slyguy.util import get_system_arch

from .constants import *
from .language import _

class APIError(Error):
    pass

class NotPairedError(APIError):
    pass

class API(object):
    def new_session(self):
        self.logged_in = False
        self._session = Session(HEADERS, timeout=30)
        self._set_authentication(userdata.get('access_token'))

    def _set_authentication(self, access_token):
        if not access_token:
            return

        self._session.headers.update({'Authorization': 'Bearer {}'.format(access_token)})
        self.logged_in = True

    def _refresh_token(self, force=False):
        if not force and userdata.get('expires', 0) > time():
            return

        payload = {
            'refresh_token': userdata.get('refresh_token'),
            'grant_type': 'refresh_token',
            'scope': 'browse video_playback device',
        }

        self._oauth_token(payload, {'Authorization': None})

    def url(self, name, path=''):
        config = self._client_config()

        if name == 'tokens':
            try:
                if config['endpoints']['getTokens']['domain'] == 'userGateway':
                    return 'https://gateway{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + config['endpoints']['getTokens']['path']
            except KeyError:
                pass

            return 'https://oauth{globalUserSubdomain}.{domain}.hbo.com/auth/tokens'.format(**config['routeKeys'])

        elif name == 'gateway':
            return 'https://gateway{userSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'comet':
            return 'https://comet{contentSubdomain}.{domain}.hbo.com'.format(**config['routeKeys']) + path

        elif name == 'artist':
            return 'https://artist.{cdnDomain}.hbo.com'.format(**config['routeKeys']) + path

        else:
            return None

    def _oauth_token(self, payload, headers=None):
        data = self._session.post(self.url('tokens'), data=payload, headers=headers).json()
        self._check_errors(data)

        self._set_authentication(data['access_token'])
        userdata.set('access_token', data['access_token'])
        userdata.set('expires', int(time() + data['expires_in'] - 15))

        if 'refresh_token' in data:
            userdata.set('refresh_token', data['refresh_token'])

    def _device_serial(self):
        def _format_id(string):
            try:
                mac_address = uuid.getnode()
                if mac_address != uuid.getnode():
                    mac_address = ''
            except:
                mac_address = ''

            system, arch = get_system_arch()
            return str(string.format(mac_address=mac_address, system=system).strip())

        return str(uuid.uuid3(uuid.UUID(UUID_NAMESPACE), _format_id(settings.get('device_id'))))

    def _guest_login(self):
        serial = self._device_serial()

        payload = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_ID,
            'scope': 'browse video_playback_free account_registration',
            'grant_type': 'client_credentials',
            'deviceSerialNumber': serial,
            'clientDeviceData': {
            	'paymentProviderCode': 'google-play'
            }
        }

        data = self._session.post(GUEST_AUTH, json=payload, headers={'Authorization': None}).json()
        if 'code' in data and data['code'] == 'invalid_credentials':
            raise APIError(_.BLOCKED_IP)

        self._check_errors(data)
        self._set_authentication(data['access_token'])
        return serial

    @mem_cache.cached(60*30)
    def _client_config(self):
        serial = self._guest_login()

        payload = {
            'contract': 'hadron:1.1.2.0',
            'preferredLanguages': ['en-us'],
        }

        data = self._session.post(CONFIG_URL, json=payload).json()
        self._set_authentication(userdata.get('access_token'))

        self._check_errors(data)
        if data['features']['currentRegionOutOfFootprint']['enabled']:
            raise APIError(_.GEO_LOCKED)

        return data

    def device_code(self):
        self.logout()

        serial = self._guest_login()

        payload = {
            'model': DEVICE_MODEL,
            'serialNumber': serial,
            'userIntent': 'login',
        }

        data = self._session.post(self.url('comet', '/devices/activationCode'), json=payload).json()
        self._check_errors(data)

        return serial, data['activationCode']

    def set_profile(self, profile_id):
        self._refresh_token()

        payload = {
            'grant_type': 'user_refresh_profile',
            'profile_id': profile_id,
            'refresh_token': userdata.get('refresh_token'),
        }

        self._oauth_token(payload)

    def device_login(self, serial, code):
        payload = {
            'model': DEVICE_MODEL,
            'code': code,
            'serialNumber': serial,
            'grant_type': 'user_activation_code',
            'scope': 'browse video_playback device elevated_account_management',
        }

        try:
            self._oauth_token(payload)
        except NotPairedError:
            return False
        else:
            return True

    def _check_errors(self, data, error=_.API_ERROR):
        if not data:
            raise APIError(_.BLOCKED_IP)

        if 'code' in data:
            if data['code'] == 'not_paired':
                raise NotPairedError()
            else:
                error_msg = data.get('message') or data.get('code')
                raise APIError(_(error, msg=error_msg))

    def profiles(self):
        self._refresh_token()
        payload = [{'id': 'urn:hbo:profiles:mine'},]

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }

        return self._session.post(self.url('comet', '/content'), json=payload, headers=headers).json()[0]['body']['profiles']

    def _age_category(self):
        month, year = userdata.get('profile', {}).get('birth', [0,0])

        i = arrow.now()
        n = i.year - year
        if i.month < month:
            n -= 1
        age = max(0, n)

        group = AGE_CATS[0][1]
        for cat in AGE_CATS:
            if age >= cat[0]:
                group = cat[1]

        return group

    @mem_cache.cached(60*30)
    def _flighted_features(self):
        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }

        return self._session.get(self.url('comet', '/flighted-features'), headers=headers).json()

    def _headwaiter(self):
        headwaiter = ''
        for key in sorted(self._client_config()['payloadValues']):
            headwaiter += '{}:{},'.format(key, self._client_config()['payloadValues'][key])

        return headwaiter.rstrip(',')

    def content(self, slug, tab=None):
        self._refresh_token()

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }

        params = self._flighted_features()['express-content']['config']['expressContentParams']
        data = self._session.get(self.url('comet', '/express-content/{}?{}'.format(slug, params)), headers=headers).json()
        self._check_errors(data)

        _data = {}
        for row in data:
            _data[row['id']] = row['body']

        return self._process(_data, tab or slug)

    def _process(self, data, slug):
        main = data[slug]
        if len(data) == 1 and 'message' in main:
            raise APIError(_(_.API_ERROR, msg=main['message']))

        def process(element):
            element['items'] = []
            element['tabs'] = []
            element['edits'] = []
            element['previews'] = []
            element['seasons'] = []
            element['extras'] = []
            element['similars'] = []
            element['episodes'] = []
            element['target'] = None

            for key in element.get('references', {}):
                if key in ('items', 'tabs', 'edits', 'seasons', 'previews', 'extras', 'similars', 'episodes'):
                    for id in element['references'][key]:
                        if id == '$dataBinding':
                            continue

                        item = {'id': id}
                        if id in data:
                            item.update(data[id])
                        process(item)
                        element[key].append(item)
                else:
                    element[key] = element['references'][key]

            element.pop('references', None)

        process(main)
        return main

    def search(self, query):
        self._refresh_token()

        payload = [{
            'id': 'urn:hbo:flexisearch:{}'.format(query),
        }]

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }

        data = self._session.post(self.url('comet', '/content'), json=payload, headers=headers).json()
        self._check_errors(data)

        keys = {}
        key = None
        for row in data:
            keys[row['id']] = row['body']
            if row['id'].startswith('urn:hbo:grid:search') and row['id'].endswith('-all'):
                key = row['id']

        if not key:
            return None

        return self._process(keys, key)

    def play(self, slug):
        self._refresh_token()

        content_data = self.content(slug)
        if not content_data['edits']:
            raise APIError(_.NO_VIDEO_FOUND)

        selected = content_data['edits'][0]
        for edit in content_data['edits']:
            for row in edit.get('textTracks', []):
                if row.get('language') == 'en-US':
                    selected = edit
                    break

        payload = [{
            'id': selected['video'],
            'headers' : {
                'x-hbo-preferred-blends': 'DASH_WDV,HSS_PR',
                'x-hbo-video-mlp': True,
            }
        }]

        headers = {
            'x-hbo-headwaiter': self._headwaiter(),
        }

        data = self._session.post(self.url('comet', '/content'), json=payload, headers=headers).json()[0]['body']

        for row in data.get('manifests', []):
            if row['type'] == 'urn:video:main':
                return row, content_data

        raise APIError(_.NO_VIDEO_FOUND)

    def logout(self):
        userdata.delete('access_token')
        userdata.delete('expires')
        userdata.delete('refresh_token')
        userdata.delete('config')
        mem_cache.empty()
        self.new_session()
